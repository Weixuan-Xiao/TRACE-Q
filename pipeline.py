"""
Q-Matrix Construction Pipeline Runner.

Flow:
1. Solve: Generate step-by-step solutions
2. Verify: Verify and correct solutions
3. Codebook: Experts + Supervisor (align → consolidate) create flat codebook
4. Tag: Multiple taggers annotate items
5. Judge: Adjudicate tagger votes (skill-level voting)
6. Aggregate: Create multiple K versions by merging skills
7. Export: Export Q-matrices and reliability report
8. Audit: Final quality review

K control:
- Default: Experts produce 3-8 skills freely.  Aggregator creates K_max-1
  and K_max-2 matrices.
- ``--target_k_exact K``: Experts + Supervisor are constrained to exactly K
  skills.  Aggregator is skipped; a single Q-matrix is exported directly.
  Use this for maximum stability.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(cmd: list[str], extra_env: dict[str, str] | None = None) -> None:
    """Run a command and print it."""
    print(">>>", " ".join(cmd))
    env = None
    if extra_env:
        env = os.environ.copy()
        env.update(extra_env)
    subprocess.check_call(cmd, env=env)


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


def _export_q_matrix_from_dossiers(
    codebook_path: Path, dossiers_path: Path, output_path: Path,
) -> None:
    """Generate step6_Q_matrix CSV directly (used when aggregator is skipped)."""
    import csv
    with open(codebook_path) as f:
        codebook = json.load(f)
    skill_ids = [s.get("skill_id") for s in codebook.get("skills", [])]

    dossiers = []
    with open(dossiers_path) as f:
        for line in f:
            line = line.strip()
            if line:
                dossiers.append(json.loads(line))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["item_id"] + skill_ids)
        writer.writeheader()
        for d in dossiers:
            item_id = str(d.get("item_id", "")).strip()
            final_skills = set()
            for s in d.get("judge", {}).get("final_skills", []):
                sid = str(s.get("skill_id", "") if isinstance(s, dict) else s).strip()
                if sid:
                    final_skills.add(sid)
            row = {"item_id": item_id}
            for sid in skill_ids:
                row[sid] = 1 if sid in final_skills else 0
            writer.writerow(row)

    print(f"Exported Q-matrix: {output_path}")


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
    parser.add_argument(
        "--target_k_exact", type=int, default=None,
        help="Fix K: experts produce exactly this many skills. Skips Aggregator.",
    )
    parser.add_argument(
        "--model", default=None,
        help="Override LLM model for all stages (sets OPENAI_MODEL env var).",
    )
    parser.add_argument(
        "--n_taggers", type=int, default=5,
        help="Number of taggers to run (default: 5).",
    )
    parser.add_argument(
        "--consensus_mode", default="threshold",
        choices=["threshold", "majority", "unanimity"],
        help="Voting consensus mode for judge (default: threshold).",
    )
    parser.add_argument("--include_threshold", type=int, default=4)
    parser.add_argument("--exclude_threshold", type=int, default=1)
    parser.add_argument(
        "--skip_stages", default="",
        help="Comma-separated stages to skip: verifier,auditor",
    )
    parser.add_argument(
        "--guides_dir", default=None,
        help="Directory containing guide files (domain_core.txt, solver_method_guide.txt, skill_ontology_guide.txt).",
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

    # Validate --skip_stages
    skip = set(s.strip() for s in args.skip_stages.split(",") if s.strip())
    allowed_skip = {"verifier", "auditor"}
    invalid_skip = skip - allowed_skip
    if invalid_skip:
        parser.error(f"Cannot skip: {invalid_skip}. Only {allowed_skip} allowed.")

    # Environment overrides (e.g. model)
    env_overrides: dict[str, str] = {}
    if args.model:
        env_overrides["OPENAI_MODEL"] = args.model

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

    def _guide_args() -> list[str]:
        return ["--guides_dir", args.guides_dir] if args.guides_dir else []

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
            ] + _guide_args(),
            extra_env=env_overrides or None,
        )
    
    # Step 2: Verify
    if args.cmd in ("verify", "all"):
        if "verifier" in skip:
            shutil.copy2(
                outputs_dir / "step1_solver_item_dossiers.jsonl",
                outputs_dir / "step2_verifier_verified_item_dossiers.jsonl",
            )
            print("SKIPPED verifier — copied step1 → step2")
        else:
            run(
                base + [
                    "main_verify.py",
                    "--input", str(outputs_dir / "step1_solver_item_dossiers.jsonl"),
                    "--out", str(outputs_dir / "step2_verifier_verified_item_dossiers.jsonl"),
                    "--prompts_dir", prompts_dir,
                ],
                extra_env=env_overrides or None,
            )
    
    # Step 3: Build Codebook (flat, K=3-8, two-phase supervisor)
    if args.cmd in ("codebook", "all"):
        codebook_cmd = base + [
            "main_taxonomist.py",
            "--input", str(outputs_dir / "step2_verifier_verified_item_dossiers.jsonl"),
            "--out", str(outputs_dir / "step3_skill_codebook.json"),
            "--out_experts", str(outputs_dir / "step3_expert_codebooks.json"),
            "--out_align", str(outputs_dir / "step3_supervisor_align_output.json"),
            "--out_supervisor", str(outputs_dir / "step3_supervisor_output.json"),
            "--prompts_dir", prompts_dir,
        ]
        if args.target_k_exact:
            codebook_cmd.extend(["--target_k_exact", str(args.target_k_exact)])
        codebook_cmd.extend(_guide_args())
        run(codebook_cmd, extra_env=env_overrides or None)
    
    # Step 4: Tag
    if args.cmd in ("tag", "all"):
        tag_cmd = base + [
            "main_taggers.py",
            "--parallel",
            "--dossiers", str(outputs_dir / "step2_verifier_verified_item_dossiers.jsonl"),
            "--codebook", str(outputs_dir / "step3_skill_codebook.json"),
            "--out_dir", str(outputs_dir / "step4_tagger_votes"),
            "--prompts_dir", prompts_dir,
            "--n_taggers", str(args.n_taggers),
        ]
        run(tag_cmd, extra_env=env_overrides or None)
    
    # Step 5: Judge
    if args.cmd in ("judge", "all"):
        judge_cmd = base + [
            "main_judge.py",
            "--dossiers", str(outputs_dir / "step2_verifier_verified_item_dossiers.jsonl"),
            "--codebook", str(outputs_dir / "step3_skill_codebook.json"),
            "--votes_dir", str(outputs_dir / "step4_tagger_votes"),
            "--out", str(outputs_dir / "step5_judge_adjudicated_dossiers.jsonl"),
            "--prompts_dir", prompts_dir,
            "--consensus_mode", args.consensus_mode,
            "--include_threshold", str(args.include_threshold),
            "--exclude_threshold", str(args.exclude_threshold),
        ]
        run(judge_cmd, extra_env=env_overrides or None)
    
    # Step 6: Aggregate (create multiple K versions)
    if args.cmd in ("aggregate", "all"):
        if args.target_k_exact:
            print(f"Skipping aggregation: --target_k_exact={args.target_k_exact}")
            # Generate Q-matrix CSV directly from adjudicated dossiers + codebook
            _export_q_matrix_from_dossiers(
                codebook_path=codebook_path,
                dossiers_path=outputs_dir / "step5_judge_adjudicated_dossiers.jsonl",
                output_path=outputs_dir / f"step6_Q_matrix_K{args.target_k_exact}.csv",
            )
        else:
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
                    ],
                    extra_env=env_overrides or None,
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
            ],
            extra_env=env_overrides or None,
        )
    
    # Step 8: Audit all K versions (K_max + aggregation targets)
    if args.cmd in ("audit", "all"):
        if "auditor" in skip:
            print("SKIPPED auditor")
        else:
            if args.target_k_exact:
                all_k = [args.target_k_exact]
            else:
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
                        ],
                        extra_env=env_overrides or None,
                    )

    # Write run_config.json at end of "all" command
    if args.cmd == "all":
        run_config = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": args.model or os.getenv("OPENAI_MODEL", ""),
            "prompts_dir": args.prompts_dir,
            "target_k_exact": args.target_k_exact,
            "n_taggers": args.n_taggers,
            "consensus_mode": args.consensus_mode,
            "include_threshold": args.include_threshold,
            "exclude_threshold": args.exclude_threshold,
            "skip_stages": args.skip_stages,
            "input": args.input,
        }
        outputs_dir.mkdir(parents=True, exist_ok=True)
        (outputs_dir / "run_config.json").write_text(
            json.dumps(run_config, indent=2) + "\n"
        )
        print(f"Run config saved to: {outputs_dir / 'run_config.json'}")


if __name__ == "__main__":
    main()
