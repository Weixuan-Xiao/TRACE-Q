"""
Step 5: Judge — Adjudicate tagger votes using skill-level voting.

Skill-level voting logic:
- For each skill, count how many taggers (out of 5) tagged it.
- auto_include (>=4/5): Strong consensus to include.
- auto_exclude (<=1/5): Weak support, exclude.
- disputed (2/5 or 3/5): Send to Judge LLM for adjudication.
- If no disputed skills, Judge is not called (saves API cost).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from dotenv import load_dotenv
from tqdm import tqdm

from src.io_utils import append_jsonl, ensure_dir, read_json, read_jsonl
from src.judge import Judge
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]


def load_votes(path: str) -> dict[str, JsonDict]:
    """Load tagger votes from a JSONL file into {item_id: vote} mapping."""
    votes: dict[str, JsonDict] = {}
    for row in read_jsonl(path):
        item_id = str(row.get("item_id", "")).strip()
        if not item_id:
            continue
        votes[item_id] = row.get("vote", {})
    return votes


def skill_set(vote: JsonDict) -> set[str]:
    """Extract skill IDs from a single tagger vote."""
    return {
        str(s.get("skill_id", "")).strip()
        for s in vote.get("skills", [])
        if str(s.get("skill_id", "")).strip()
    }


def compute_skill_level_votes(
    votes_by_tagger: dict[str, JsonDict],
    include_threshold: int = 4,
    exclude_threshold: int = 1,
) -> JsonDict:
    """
    Compute per-skill vote counts and categorize skills.

    Returns dict with:
        skill_counts: {skill_id: int} — how many taggers tagged each skill
        auto_include: list of skill_ids with count >= include_threshold
        auto_exclude: list of skill_ids with count <= exclude_threshold
        disputed: list of skill_ids in between
        has_disputed: bool — whether any skills need Judge adjudication
        n_taggers: int — total number of taggers
    """
    n_taggers = len(votes_by_tagger)
    skill_counts: dict[str, int] = {}

    for _tid, vote in votes_by_tagger.items():
        tagged_skills = skill_set(vote)
        for sid in tagged_skills:
            skill_counts[sid] = skill_counts.get(sid, 0) + 1

    auto_include: list[str] = []
    auto_exclude: list[str] = []
    disputed: list[str] = []

    for sid, count in sorted(skill_counts.items()):
        if count >= include_threshold:
            auto_include.append(sid)
        elif count <= exclude_threshold:
            auto_exclude.append(sid)
        else:
            disputed.append(sid)

    return {
        "skill_counts": skill_counts,
        "auto_include": sorted(auto_include),
        "auto_exclude": sorted(auto_exclude),
        "disputed": sorted(disputed),
        "has_disputed": len(disputed) > 0,
        "n_taggers": n_taggers,
    }


def compute_majority_votes(votes_by_tagger: dict[str, JsonDict]) -> JsonDict:
    """Include if > 50% of taggers agree."""
    n_taggers = len(votes_by_tagger)
    threshold = n_taggers / 2
    skill_counts: dict[str, int] = {}
    for _tid, vote in votes_by_tagger.items():
        for sid in skill_set(vote):
            skill_counts[sid] = skill_counts.get(sid, 0) + 1
    return {
        "skill_counts": skill_counts,
        "auto_include": sorted(s for s, c in skill_counts.items() if c > threshold),
        "auto_exclude": sorted(s for s, c in skill_counts.items() if c <= threshold),
        "disputed": [],
        "has_disputed": False,
        "n_taggers": n_taggers,
    }


def compute_unanimity_votes(votes_by_tagger: dict[str, JsonDict]) -> JsonDict:
    """Include only if ALL taggers agree."""
    n_taggers = len(votes_by_tagger)
    skill_counts: dict[str, int] = {}
    for _tid, vote in votes_by_tagger.items():
        for sid in skill_set(vote):
            skill_counts[sid] = skill_counts.get(sid, 0) + 1
    return {
        "skill_counts": skill_counts,
        "auto_include": sorted(s for s, c in skill_counts.items() if c == n_taggers),
        "auto_exclude": sorted(s for s, c in skill_counts.items() if c < n_taggers),
        "disputed": [],
        "has_disputed": False,
        "n_taggers": n_taggers,
    }


def merge_evidence_for_skills(
    votes_by_tagger: dict[str, JsonDict],
    skill_ids: list[str],
) -> list[JsonDict]:
    """
    Merge evidence_step_ids from all taggers who tagged each skill.

    For auto-included skills, merges evidence from all taggers that
    tagged the skill (union of evidence_step_ids).

    Args:
        votes_by_tagger: {tagger_id: vote}
        skill_ids: list of skill_ids to merge evidence for

    Returns:
        List of {"skill_id", "evidence_step_ids", "confidence"}
    """
    skill_id_set = set(skill_ids)
    merged: dict[str, set[str]] = {}

    for _tid, vote in votes_by_tagger.items():
        for s in vote.get("skills", []):
            sid = str(s.get("skill_id", "")).strip()
            if sid not in skill_id_set:
                continue
            merged.setdefault(sid, set()).update(
                str(e).strip()
                for e in s.get("evidence_step_ids", [])
                if str(e).strip()
            )

    return [
        {
            "skill_id": sid,
            "evidence_step_ids": sorted(list(merged.get(sid, set()))),
            "confidence": 1.0,
        }
        for sid in sorted(skill_ids)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adjudicate tagger votes using skill-level voting."
    )
    parser.add_argument(
        "--dossiers",
        default="outputs/step2_verifier_verified_item_dossiers.jsonl",
        help="Verified dossiers JSONL",
    )
    parser.add_argument(
        "--codebook",
        default="outputs/step3_taxonomist_skill_codebook_v1.json",
        help="Codebook JSON",
    )
    parser.add_argument(
        "--votes_dir",
        default="outputs/step4_tagger_votes",
        help="Directory containing T1..T5 vote files",
    )
    parser.add_argument(
        "--out",
        default="outputs/step5_judge_adjudicated_dossiers.jsonl",
        help="Output adjudicated dossiers JSONL",
    )
    parser.add_argument(
        "--prompts_dir",
        default="prompts/v1",
        help="Directory containing prompt files (judge.txt, etc.)",
    )
    parser.add_argument("--include_threshold", type=int, default=4)
    parser.add_argument("--exclude_threshold", type=int, default=1)
    parser.add_argument(
        "--consensus_mode", default="threshold",
        choices=["threshold", "majority", "unanimity"],
    )
    args = parser.parse_args()

    load_dotenv(override=False)
    ensure_dir(str(Path(args.out).parent))
    Path(args.out).unlink(missing_ok=True)
    seen: set[str] = set()

    dossiers = read_jsonl(args.dossiers)
    codebook = read_json(args.codebook)

    vote_files = sorted(Path(args.votes_dir).glob("T*.jsonl"))
    if not vote_files:
        raise RuntimeError(f"No tagger vote files found in {args.votes_dir}")
    all_votes: dict[str, dict[str, JsonDict]] = {}
    for vf in vote_files:
        all_votes[vf.stem] = load_votes(str(vf))
    print(f"Loaded {len(all_votes)} tagger files: {sorted(all_votes.keys())}")

    llm = LLMClient()
    judge = Judge(llm=llm, prompt_path=str(Path(args.prompts_dir) / "judge.txt"))

    # Counters for summary
    n_auto = 0
    n_judge = 0

    for d in tqdm(dossiers, desc="Adjudicating", unit="item"):
        item_id = str(d.get("item_id", "")).strip()
        if not item_id:
            raise ValueError(f"Missing item_id in dossier: {d}")
        if item_id in seen:
            continue

        votes_bundle: dict[str, JsonDict] = {}
        for tid, votes_map in all_votes.items():
            v = votes_map.get(item_id)
            if v is None:
                raise RuntimeError(f"Missing vote for {item_id} from {tid}")
            votes_bundle[tid] = v

        # --- Skill-level voting ---
        if args.consensus_mode == "majority":
            vote_stats = compute_majority_votes(votes_bundle)
        elif args.consensus_mode == "unanimity":
            vote_stats = compute_unanimity_votes(votes_bundle)
        else:
            vote_stats = compute_skill_level_votes(
                votes_bundle, args.include_threshold, args.exclude_threshold)

        if not vote_stats["has_disputed"]:
            # All skills are clear — no Judge call needed
            final_skills = merge_evidence_for_skills(
                votes_bundle, vote_stats["auto_include"]
            )
            judge_out: JsonDict = {
                "final_skills": final_skills,
                "judge_notes": (
                    f"Skill-level voting: no disputed skills. "
                    f"Auto-included (>=4/5): {vote_stats['auto_include']}. "
                    f"Auto-excluded (<=1/5): {vote_stats['auto_exclude']}."
                ),
            }
            n_auto += 1
        else:
            # Disputed skills exist — call Judge with vote context
            judge_out = judge.adjudicate(
                codebook=codebook,
                dossier=d,
                votes=votes_bundle,
                vote_stats=vote_stats,
            )
            n_judge += 1

        # Attach vote_stats for traceability
        judge_out["vote_stats"] = vote_stats

        adjudicated = {
            "item_id": item_id,
            "item": d.get("item", {}),
            "solver": d.get("solver", {}),
            "verifier": d.get("verifier", {}),
            "tagger_votes": votes_bundle,
            "judge": judge_out,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "stage": "adjudicated",
        }

        append_jsonl(args.out, [adjudicated])
        seen.add(item_id)

    # Print summary
    total = n_auto + n_judge
    print(f"\n=== Adjudication Complete ===")
    print(f"Total items: {total}")
    print(f"  Auto-resolved (no disputed skills): {n_auto}")
    print(f"  Judge-adjudicated (disputed skills): {n_judge}")


if __name__ == "__main__":
    main()
