"""
Q-Matrix Construction Pipeline Runner.

Flow (Bottom-Up + Aggregator):
1. Solve: Generate step-by-step solutions
2. Verify: Verify and correct solutions
3. Codebook: Experts + Supervisor (align → consolidate) create flat codebook (K=3-8)
4. Tag: Multiple taggers annotate items
5. Judge: Adjudicate tagger votes (skill-level voting)
6. Aggregate: Create multiple K versions by merging
7. Export: Export Q-matrices and reliability report
8. Audit: Final quality review
"""
from __future__ import annotations

import argparse
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
        default="6,5,4",
        help="Comma-separated target K values for aggregation.",
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
        run(
            base + [
                "main_aggregator.py",
                "--codebook", str(outputs_dir / "step3_skill_codebook.json"),
                "--dossiers", str(outputs_dir / "step5_judge_adjudicated_dossiers.jsonl"),
                "--target_k", args.target_k,
                "--out_dir", str(outputs_dir),
                "--prompts_dir", prompts_dir,
            ]
        )
    
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
    
    # Step 8: Audit all K versions
    if args.cmd in ("audit", "all"):
        import json
        
        # Load original codebook to get K_max
        with open(outputs_dir / "step3_skill_codebook.json") as f:
            original_codebook = json.load(f)
        k_max = len(original_codebook.get("skills", []))
        
        # Build list of K values to audit: [K_max] + target_k values
        target_k_values = [int(k.strip()) for k in args.target_k.split(",")]
        all_k_values = [k_max] + target_k_values
        
        print(f"\n=== Auditing Q-matrices for K values: {all_k_values} ===")
        
        for k_val in all_k_values:
            print(f"\n--- Auditing K={k_val} ---")
            
            # Determine codebook and Q-matrix paths for this K
            if k_val == k_max:
                codebook_path = outputs_dir / "step3_skill_codebook.json"
                q_matrix_path = outputs_dir / f"step6_Q_matrix_K{k_val}.csv"
            else:
                codebook_path = outputs_dir / f"step6_codebook_K{k_val}.json"
                q_matrix_path = outputs_dir / f"step6_Q_matrix_K{k_val}.csv"
            
            # Check if files exist
            if not q_matrix_path.exists():
                print(f"  Skipping K={k_val}: Q-matrix not found at {q_matrix_path}")
                continue
            if not codebook_path.exists():
                print(f"  Skipping K={k_val}: Codebook not found at {codebook_path}")
                continue
            
            # Output paths for this K version
            out_review = outputs_dir / f"step8_auditor_review_K{k_val}.jsonl"
            out_q_matrix = outputs_dir / f"step8_auditor_Q_matrix_K{k_val}_reviewed.csv"
            out_summary = outputs_dir / f"step8_auditor_summary_K{k_val}.md"
            
            run(
                base + [
                    "main_auditor.py",
                    "--dossiers", str(outputs_dir / "step2_verifier_verified_item_dossiers.jsonl"),
                    "--codebook", str(codebook_path),
                    "--q_matrix", str(q_matrix_path),
                    "--reliability", str(outputs_dir / "step7_export_reliability_per_item.csv"),
                    "--out_review", str(out_review),
                    "--out_q_matrix", str(out_q_matrix),
                    "--out_summary", str(out_summary),
                    "--prompts_dir", prompts_dir,
                ]
            )


if __name__ == "__main__":
    main()
