#!/usr/bin/env python3
"""
Step 7: Auditor - Reviews and corrects Q-matrix annotations.

Inputs:
  - step2_verifier_verified_item_dossiers.jsonl (stem_text, solution_steps)
  - step3_taxonomist_skill_codebook_v1.json (skill definitions)
  - step6_export_Q_matrix_v1.csv (current Q-matrix to audit)
  - step6_export_reliability_per_item.csv (tagger agreement info)

Outputs:
  - step7_auditor_review.jsonl (detailed audit results per item)
  - step7_auditor_Q_matrix_reviewed.csv (corrected Q-matrix with * flags)
  - step7_auditor_summary.md (audit summary report)
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

from dotenv import load_dotenv
from tqdm import tqdm

from src.auditor import Auditor
from src.io_utils import append_jsonl, ensure_dir, read_json, read_jsonl
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]


def read_csv_as_dicts(path: str) -> List[JsonDict]:
    """Read a CSV file and return a list of dicts."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def parse_q_matrix(q_matrix_rows: List[JsonDict]) -> Dict[str, Dict[str, int]]:
    """
    Parse Q-matrix CSV rows into {item_id: {skill_id: 0/1}}.
    Handles both original (S01, S02...) and merged (M01, M02...) skill IDs.
    """
    result = {}
    for row in q_matrix_rows:
        item_id = row.get("item_id", "").strip()
        if not item_id:
            continue
        skills = {}
        for key, val in row.items():
            # Handle both S## (original) and M## (merged) skill IDs
            if key != "item_id" and (key.startswith("S") or key.startswith("M")):
                skills[key] = int(val) if val in ("0", "1") else 0
        result[item_id] = skills
    return result


def parse_reliability(reliability_rows: List[JsonDict]) -> Dict[str, JsonDict]:
    """
    Parse reliability CSV rows into {item_id: {full_agree_5, ...}}.
    """
    result = {}
    for row in reliability_rows:
        item_id = row.get("item_id", "").strip()
        if not item_id:
            continue
        result[item_id] = {
            "full_agree_5": row.get("full_agree_5", "0") == "1",
            "supermajority_4of5": row.get("supermajority_4of5", "0") == "1",
            "avg_jaccard": row.get("avg_pairwise_jaccard_10pairs", "0"),
            "adjudication_needed": row.get("adjudication_needed", "0") == "1",
        }
    return result


def get_current_skills(item_q: Dict[str, int]) -> List[str]:
    """Get list of skill IDs marked as 1."""
    return sorted([sid for sid, val in item_q.items() if val == 1])


def write_reviewed_q_matrix(
    path: str,
    original_q: Dict[str, Dict[str, int]],
    audit_results: Dict[str, JsonDict],
    skill_ids: List[str],
) -> None:
    """
    Write the reviewed Q-matrix CSV with corrections and * flags.
    """
    with open(path, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["item_id"] + skill_ids + ["audit_verdict"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item_id in sorted(original_q.keys()):
            row = {"item_id": item_id}
            original = original_q[item_id]
            audit = audit_results.get(item_id, {})
            verdict = audit.get("verdict", "correct")
            corrections = audit.get("corrections", {})
            add_skills = set(corrections.get("add_skills", []))
            remove_skills = set(corrections.get("remove_skills", []))
            controversy_flags = audit.get("controversy_flags", [])
            is_controversial = verdict == "controversial" or "tagger_disagreement" in controversy_flags

            for sid in skill_ids:
                orig_val = original.get(sid, 0)
                # Apply corrections
                if sid in add_skills:
                    new_val = 1
                elif sid in remove_skills:
                    new_val = 0
                else:
                    new_val = orig_val

                # Add * flag for controversial items
                if is_controversial and (sid in add_skills or sid in remove_skills):
                    row[sid] = f"{new_val}*"
                else:
                    row[sid] = str(new_val)

            row["audit_verdict"] = verdict
            writer.writerow(row)


def write_summary_report(
    path: str,
    audit_results: Dict[str, JsonDict],
    codebook: JsonDict,
) -> None:
    """Write audit summary report in Markdown."""
    verdicts = Counter(r.get("verdict", "correct") for r in audit_results.values())
    total = len(audit_results)

    lines = [
        "# Q-Matrix Audit Summary Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Overview",
        "",
        f"- Total items audited: {total}",
        f"- Correct: {verdicts.get('correct', 0)} ({100*verdicts.get('correct', 0)/total:.1f}%)" if total > 0 else "- Correct: 0",
        f"- Errors (corrected): {verdicts.get('error', 0)} ({100*verdicts.get('error', 0)/total:.1f}%)" if total > 0 else "- Errors: 0",
        f"- Controversial: {verdicts.get('controversial', 0)} ({100*verdicts.get('controversial', 0)/total:.1f}%)" if total > 0 else "- Controversial: 0",
        "",
        "## Items Requiring Attention",
        "",
    ]

    # List errors and controversial items
    attention_items = [
        (item_id, r) for item_id, r in audit_results.items()
        if r.get("verdict") in ("error", "controversial")
    ]

    if attention_items:
        lines.append("| Item ID | Verdict | Add Skills | Remove Skills | Reasoning |")
        lines.append("|---------|---------|------------|---------------|-----------|")
        for item_id, r in sorted(attention_items):
            corrections = r.get("corrections", {})
            add_s = ", ".join(corrections.get("add_skills", [])) or "-"
            rem_s = ", ".join(corrections.get("remove_skills", [])) or "-"
            reasoning = corrections.get("reasoning", "")[:100].replace("|", "/").replace("\n", " ")
            if len(corrections.get("reasoning", "")) > 100:
                reasoning += "..."
            lines.append(f"| {item_id} | {r.get('verdict')} | {add_s} | {rem_s} | {reasoning} |")
    else:
        lines.append("No items require attention. All annotations are correct.")

    lines.extend([
        "",
        "## Skill Codebook Reference",
        "",
        "| Skill ID | Name | Definition |",
        "|----------|------|------------|",
    ])

    for skill in codebook.get("skills", []):
        # Handle both original (skill_id) and aggregated (merged_id) formats
        sid = skill.get("skill_id") or skill.get("merged_id", "")
        name = skill.get("name", "").replace("|", "/")
        defn = skill.get("definition", "")[:80].replace("|", "/").replace("\n", " ")
        if len(skill.get("definition", "")) > 80:
            defn += "..."
        lines.append(f"| {sid} | {name} | {defn} |")

    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 7: Audit Q-matrix annotations.")
    parser.add_argument(
        "--dossiers",
        default="outputs/step2_verifier_verified_item_dossiers.jsonl",
        help="Verified dossiers JSONL",
    )
    parser.add_argument(
        "--codebook",
        default="outputs/step3_taxonomist_skill_codebook_v1.json",
        help="Skill codebook JSON",
    )
    parser.add_argument(
        "--q_matrix",
        default="outputs/step6_export_Q_matrix_v1.csv",
        help="Current Q-matrix CSV to audit",
    )
    parser.add_argument(
        "--reliability",
        default="outputs/step6_export_reliability_per_item.csv",
        help="Reliability per item CSV",
    )
    parser.add_argument(
        "--out_review",
        default="outputs/step7_auditor_review.jsonl",
        help="Output audit review JSONL",
    )
    parser.add_argument(
        "--out_q_matrix",
        default="outputs/step7_auditor_Q_matrix_reviewed.csv",
        help="Output reviewed Q-matrix CSV",
    )
    parser.add_argument(
        "--out_summary",
        default="outputs/step7_auditor_summary.md",
        help="Output audit summary report MD",
    )
    parser.add_argument(
        "--prompts_dir",
        default="prompts/v5_guided",
        help="Directory containing prompt files (auditor.txt, etc.)",
    )
    args = parser.parse_args()

    load_dotenv(override=False)
    ensure_dir(str(Path(args.out_review).parent))

    # Clear output files
    Path(args.out_review).unlink(missing_ok=True)
    Path(args.out_q_matrix).unlink(missing_ok=True)
    Path(args.out_summary).unlink(missing_ok=True)

    # Load inputs
    print("Loading inputs...")
    dossiers = read_jsonl(args.dossiers)
    codebook = read_json(args.codebook)
    q_matrix_rows = read_csv_as_dicts(args.q_matrix)
    reliability_rows = read_csv_as_dicts(args.reliability)

    # Parse into usable structures
    q_matrix = parse_q_matrix(q_matrix_rows)
    reliability = parse_reliability(reliability_rows)

    # Build dossier lookup
    dossier_lookup: Dict[str, JsonDict] = {}
    for d in dossiers:
        item_id = str(d.get("item_id", "")).strip()
        if item_id:
            dossier_lookup[item_id] = d

    # Get skill IDs from codebook (handle both original and aggregated formats)
    # Original codebook uses "skill_id", aggregated uses "merged_id"
    skill_ids = []
    for s in codebook.get("skills", []):
        sid = s.get("skill_id") or s.get("merged_id", "")
        if sid:
            skill_ids.append(sid)
    skill_ids = sorted(skill_ids)

    # Initialize Auditor
    llm = LLMClient()
    auditor = Auditor(llm=llm, prompt_path=str(Path(args.prompts_dir) / "auditor.txt"))

    # Audit each item
    audit_results: Dict[str, JsonDict] = {}
    print(f"\nAuditing {len(q_matrix)} items...")

    for item_id in tqdm(sorted(q_matrix.keys()), desc="Auditing", unit="item"):
        dossier = dossier_lookup.get(item_id, {})
        item_data = dossier.get("item", {})
        solver_data = dossier.get("solver", {})

        stem_text = str(item_data.get("stem_text", ""))
        solution_steps = solver_data.get("solution_steps", [])

        item_q = q_matrix.get(item_id, {})
        current_skills = get_current_skills(item_q)

        rel_info = reliability.get(item_id, {})
        full_agree = rel_info.get("full_agree_5", True)
        tagger_agreement = "5/5" if full_agree else ("4/5" if rel_info.get("supermajority_4of5") else "<4/5")

        # Call Auditor
        result = auditor.audit_item(
            item_id=item_id,
            stem_text=stem_text,
            solution_steps=solution_steps,
            codebook=codebook,
            current_skills=current_skills,
            tagger_agreement=tagger_agreement,
            full_agree=full_agree,
        )

        # Add metadata
        result["original_skills"] = current_skills
        result["tagger_agreement"] = tagger_agreement
        result["created_at"] = datetime.now(timezone.utc).isoformat()

        audit_results[item_id] = result

        # Append to review file
        append_jsonl(args.out_review, [result])

    # Write reviewed Q-matrix
    print(f"\nWriting reviewed Q-matrix to {args.out_q_matrix}...")
    write_reviewed_q_matrix(args.out_q_matrix, q_matrix, audit_results, skill_ids)

    # Write summary report
    print(f"Writing summary report to {args.out_summary}...")
    write_summary_report(args.out_summary, audit_results, codebook)

    # Print summary
    verdicts = Counter(r.get("verdict", "correct") for r in audit_results.values())
    print(f"\n=== Audit Complete ===")
    print(f"Total items: {len(audit_results)}")
    print(f"  - Correct: {verdicts.get('correct', 0)}")
    print(f"  - Errors (corrected): {verdicts.get('error', 0)}")
    print(f"  - Controversial: {verdicts.get('controversial', 0)}")


if __name__ == "__main__":
    main()

