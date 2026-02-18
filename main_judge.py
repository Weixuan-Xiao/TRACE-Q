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
) -> JsonDict:
    """
    Compute per-skill vote counts and categorize skills.

    Returns dict with:
        skill_counts: {skill_id: int} — how many taggers tagged each skill
        auto_include: list of skill_ids with count >= 4
        auto_exclude: list of skill_ids with count <= 1
        disputed: list of skill_ids with count 2 or 3
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
        if count >= 4:
            auto_include.append(sid)
        elif count <= 1:
            auto_exclude.append(sid)
        else:  # 2 or 3
            disputed.append(sid)

    return {
        "skill_counts": skill_counts,
        "auto_include": sorted(auto_include),
        "auto_exclude": sorted(auto_exclude),
        "disputed": sorted(disputed),
        "has_disputed": len(disputed) > 0,
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
    args = parser.parse_args()

    load_dotenv(override=False)
    ensure_dir(str(Path(args.out).parent))
    Path(args.out).unlink(missing_ok=True)
    seen: set[str] = set()

    dossiers = read_jsonl(args.dossiers)
    codebook = read_json(args.codebook)

    v1 = load_votes(str(Path(args.votes_dir) / "T1.jsonl"))
    v2 = load_votes(str(Path(args.votes_dir) / "T2.jsonl"))
    v3 = load_votes(str(Path(args.votes_dir) / "T3.jsonl"))
    v4 = load_votes(str(Path(args.votes_dir) / "T4.jsonl"))
    v5 = load_votes(str(Path(args.votes_dir) / "T5.jsonl"))

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

        vote_T1 = v1.get(item_id)
        vote_T2 = v2.get(item_id)
        vote_T3 = v3.get(item_id)
        vote_T4 = v4.get(item_id)
        vote_T5 = v5.get(item_id)
        if any(v is None for v in [vote_T1, vote_T2, vote_T3, vote_T4, vote_T5]):
            raise RuntimeError(
                f"Missing votes for item_id={item_id}. "
                f"Ensure T1..T5 vote files are complete."
            )

        votes_bundle = {
            "T1": vote_T1, "T2": vote_T2, "T3": vote_T3,
            "T4": vote_T4, "T5": vote_T5,
        }

        # --- Skill-level voting ---
        vote_stats = compute_skill_level_votes(votes_bundle)

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
