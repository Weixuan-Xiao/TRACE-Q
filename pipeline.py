"""
Q-Matrix Construction Pipeline Runner.

Flow:
1. Solve: Generate step-by-step solutions
2. Verify: Verify and correct solutions
3. Codebook: Experts + Supervisor (align → consolidate) create flat codebook (K=3-8)
4. Tag: Multiple taggers annotate items
5. Judge: Adjudicate tagger votes (skill-level voting)
6. Aggregate: Create multiple K versions by merging
7. Export: Export Q-matrices and reliability report
8. Audit: Final quality review

When running "all", target_k for aggregation is auto-computed from codebook K_max
as [K_max-1, K_max-2, ..., 3]. You can override with --target_k.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    """Run a command and print it."""
    print(">>>", " ".join(cmd))
    subprocess.check_call(cmd)


def clear_outputs(outputs_dir: Path) -> None:
    """Remove step-prefixed output files/dirs for fresh run."""
    outputs_dir.mkdir(parents=True, exist_ok=True)
    for p in outputs_dir.glob("step*_*.jsonl"):
        p.unlink(missing_ok=True)
    for p in outputs_dir.glob("step*_*.json"):
        p.unlink(missing_ok=True)
    for p in outputs_dir.glob("step*_*.csv"):
        p.unlink(missing_ok=True)
    for p in outputs_dir.glob("step*_*.md"):
        p.unlink(missing_ok=True)
    tv = outputs_dir / "step4_tagger_votes"
    if tv.exists():
        shutil.rmtree(tv)


def main() -> None:
    parser = argparse.ArgumentParser(description="Q-matrix pipeline runner.")
    parser.add_argument(
        "--outputs_dir",
        default="outputs",
        help="Output directory for this run.",
    )
    parser.add_argument(
        "--prompts_dir",
        default="prompts/v2",
        help="Directory containing prompt files.",
    )
    parser.add_argument(
        "--input",
        default="data/items.jsonl",
        help="Input JSONL path for items.",
    )
    parser.add_argument(
        "--target_k",
        default="auto",
        help=(
            "Comma-separated target K values for aggregation, e.g. '6,5,4'. "
            "Use 'auto' (default) to derive from codebook: K_max-1 down to 3."
        ),
    )
    
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("solve", help="Step 1: Solve items")
    sub.add_parser("verify", help="Step 2: Verify solutions")
    sub.add_parser("codebook", help="Step 3: Build skill codebook (K=3-8)")
    sub.add_parser("tag", help="Step 4: Tag items with skills")
    sub.add_parser("judge", help="Step 5: Adjudicate tagger votes")
    sub.add_parser("aggregate", help="Step 6: Aggregate to multiple K levels")
    sub.add_parser("export", help="Step 7: Export reliability report")
    sub.add_parser("audit", help="Step 8: Audit Q-matrix")
    sub.add_parser("all", help="Run all steps")
    
    args = parser.parse_args()

    base = [sys.executable]
    outputs_dir = Path(args.outputs_dir)
    prompts_dir = str(args.prompts_dir)
    codebook_path = outputs_dir / "step3_skill_codebook.json"

    def resolve_target_k() -> str:
        """
        Resolve --target_k to a concrete comma-separated string.

        If 'auto', read K_max from the codebook and return 'K_max-1,...,3'.
        Otherwise return the user-provided value as-is.
        """
        if args.target_k != "auto":
            return args.target_k

        if not codebook_path.exists():
            print("WARNING: codebook not found, falling back to target_k='6,5,4'")
            return "6,5,4"

        with open(codebook_path) as f:
            cb = json.load(f)
        k_max = len(cb.get("skills", []))
        if k_max <= 3:
            # No room to aggregate further
            print(f"Codebook K_max={k_max}, no aggregation targets possible.")
            return ""
        # At most 2 lower levels: K_max-1 and K_max-2 (total ≤ 3 Q-matrices)
        targets = [k for k in [k_max - 1, k_max - 2] if k >= 3]
        result = ",".join(str(k) for k in targets)
        print(f"Auto target_k: K_max={k_max} → targets={result}")
        return result

    def get_all_k_values() -> list[int]:
        """
        Get all K values to audit: [K_max] + aggregation targets.

        Reads K_max from codebook, then derives targets the same way
        as resolve_target_k().
        """
        if not codebook_path.exists():
            return []
        with open(codebook_path) as f:
            k_max = len(json.load(f).get("skills", []))
        target_k_str = resolve_target_k()
        targets = [int(k.strip()) for k in target_k_str.split(",") if k.strip()]
        return [k_max] + targets

    # Step 1: Solve
    if args.cmd in ("solve", "all"):
        if args.cmd == "all":
            clear_outputs(outputs_dir)
        run(
            base + [
                "main.py",
                "--input", args.input,
                "--out", str(outputs_dir / "step1_solver_item_dossiers.jsonl"),
                "--prompts_dir", prompts_dir,
            ]
        )
    
    # Step 2: Verify
    if args.cmd in ("verify", "all"):
        run(
            base + [
                "main_verify.py",
                "--input", str(outputs_dir / "step1_solver_item_dossiers.jsonl"),
                "--out", str(outputs_dir / "step2_verifier_verified_item_dossiers.jsonl"),
                "--prompts_dir", prompts_dir,
            ]
        )
    
    # Step 3: Build Codebook (flat, K=3-8, two-phase supervisor)
    if args.cmd in ("codebook", "all"):
        run(
            base + [
                "main_taxonomist.py",
                "--input", str(outputs_dir / "step2_verifier_verified_item_dossiers.jsonl"),
                "--out", str(outputs_dir / "step3_skill_codebook.json"),
                "--out_experts", str(outputs_dir / "step3_expert_codebooks.json"),
                "--out_align", str(outputs_dir / "step3_supervisor_align_output.json"),
                "--out_supervisor", str(outputs_dir / "step3_supervisor_output.json"),
                "--prompts_dir", prompts_dir,
            ]
        )
    
    # Step 4: Tag
    if args.cmd in ("tag", "all"):
        run(
            base + [
                "main_taggers.py",
                "--parallel",
                "--dossiers", str(outputs_dir / "step2_verifier_verified_item_dossiers.jsonl"),
                "--codebook", str(outputs_dir / "step3_skill_codebook.json"),
                "--out_dir", str(outputs_dir / "step4_tagger_votes"),
                "--prompts_dir", prompts_dir,
            ]
        )
    
    # Step 5: Judge
    if args.cmd in ("judge", "all"):
        run(
            base + [
                "main_judge.py",
                "--dossiers", str(outputs_dir / "step2_verifier_verified_item_dossiers.jsonl"),
                "--codebook", str(outputs_dir / "step3_skill_codebook.json"),
                "--votes_dir", str(outputs_dir / "step4_tagger_votes"),
                "--out", str(outputs_dir / "step5_judge_adjudicated_dossiers.jsonl"),
                "--prompts_dir", prompts_dir,
            ]
        )
    
    # Step 6: Aggregate (create multiple K versions)
    if args.cmd in ("aggregate", "all"):
        target_k_str = resolve_target_k()
        if target_k_str:
            run(
                base + [
                    "main_aggregator.py",
                    "--codebook", str(codebook_path),
                    "--dossiers", str(outputs_dir / "step5_judge_adjudicated_dossiers.jsonl"),
                    "--target_k", target_k_str,
                    "--out_dir", str(outputs_dir),
                    "--prompts_dir", prompts_dir,
                ]
            )
        else:
            print("Skipping aggregation: no valid target K values.")
    
    # Step 7: Export reliability report
    if args.cmd in ("export", "all"):
        run(
            base + [
                "main_export_q.py",
                "--dossiers", str(outputs_dir / "step5_judge_adjudicated_dossiers.jsonl"),
                "--codebook", str(outputs_dir / "step3_skill_codebook.json"),
                "--out_dir", str(outputs_dir),
                "--prefix", "step7_export",
            ]
        )
    
    # Step 8: Audit all K versions (K_max + aggregation targets)
    if args.cmd in ("audit", "all"):
        all_k = get_all_k_values()

        if not all_k:
            print("\n=== Audit: codebook not found. Skipping. ===")
        else:
            k_max = all_k[0]
            print(f"\n=== Auditing Q-matrices for K values: {all_k} ===")

            for k_val in all_k:
                # K_max uses original codebook; aggregated Ks use step6_codebook
                if k_val == k_max:
                    cb_path = codebook_path
                else:
                    cb_path = outputs_dir / f"step6_codebook_K{k_val}.json"
                q_path = outputs_dir / f"step6_Q_matrix_K{k_val}.csv"

                if not q_path.exists():
                    print(f"\n--- Skipping K={k_val}: {q_path.name} not found ---")
                    continue
                if not cb_path.exists():
                    print(f"\n--- Skipping K={k_val}: {cb_path.name} not found ---")
                    continue

                print(f"\n--- Auditing K={k_val} ---")

                out_review = outputs_dir / f"step8_auditor_review_K{k_val}.jsonl"
                out_q_matrix = outputs_dir / f"step8_auditor_Q_matrix_K{k_val}_reviewed.csv"
                out_summary = outputs_dir / f"step8_auditor_summary_K{k_val}.md"

                run(
                    base + [
                        "main_auditor.py",
                        "--dossiers", str(outputs_dir / "step2_verifier_verified_item_dossiers.jsonl"),
                        "--codebook", str(cb_path),
                        "--q_matrix", str(q_path),
                        "--reliability", str(outputs_dir / "step7_export_reliability_per_item.csv"),
                        "--out_review", str(out_review),
                        "--out_q_matrix", str(out_q_matrix),
                        "--out_summary", str(out_summary),
                        "--prompts_dir", prompts_dir,
                    ]
                )


if __name__ == "__main__":
    main()
