from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(cmd: list[str]) -> None:
    print(">>>", " ".join(cmd))
    subprocess.check_call(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run repeated pipeline experiments across prompt versions and store outputs in separate folders."
    )
    parser.add_argument(
        "--cmd",
        default="all",
        choices=["solve", "verify", "codebook", "tag", "judge", "aggregate", "export", "audit", "all"],
        help="Which pipeline command to run each time.",
    )
    parser.add_argument(
        "--prompt_version",
        default="v1",
        help='Prompt version folder under prompts/, e.g. "v1" or "v2".',
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="How many repeated runs to execute.",
    )
    parser.add_argument(
        "--start_run",
        type=int,
        default=1,
        help="Starting run index (use to resume, e.g. --start_run 2 --runs 10 runs run2‑run10).",
    )
    parser.add_argument(
        "--base_outputs",
        default="outputs_exp",
        help="Base directory for experiment outputs.",
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
            "Use 'auto' (default) to let pipeline derive from codebook K_max."
        ),
    )
    parser.add_argument(
        "--target_k_exact", type=int, default=None,
        help="Fix K: experts produce exactly this many skills. Skips Aggregator.",
    )
    parser.add_argument("--model", default=None, help="Override LLM model for all stages.")
    parser.add_argument("--n_taggers", type=int, default=5, help="Number of taggers (default: 5).")
    parser.add_argument(
        "--consensus_mode", default="threshold",
        choices=["threshold", "majority", "unanimity"],
    )
    parser.add_argument("--include_threshold", type=int, default=4)
    parser.add_argument("--exclude_threshold", type=int, default=1)
    parser.add_argument("--skip_stages", default="", help="Comma-separated: verifier,auditor")
    args = parser.parse_args()

    prompts_dir = Path("prompts") / args.prompt_version
    if not prompts_dir.exists():
        raise SystemExit(
            f"prompts_dir not found: {prompts_dir}. Create it (e.g., copy prompts/ into prompts/{args.prompt_version}/) first."
        )

    base_outputs = Path(args.base_outputs)
    base_outputs.mkdir(parents=True, exist_ok=True)

    meta_common = {
        "cmd": args.cmd,
        "prompt_version": args.prompt_version,
        "prompts_dir": str(prompts_dir),
        "input": args.input,
        "target_k": args.target_k,
        "target_k_exact": args.target_k_exact,
        "model": args.model,
        "n_taggers": args.n_taggers,
        "consensus_mode": args.consensus_mode,
        "include_threshold": args.include_threshold,
        "exclude_threshold": args.exclude_threshold,
        "skip_stages": args.skip_stages,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.executable,
    }

    for i in range(args.start_run, args.runs + 1):
        run_dir = base_outputs / args.prompt_version / f"run{i}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Store run metadata for reproducibility.
        meta = dict(meta_common)
        meta["run_index"] = i
        (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

        cmd_args = [
            sys.executable,
            "pipeline.py",
            "--outputs_dir",
            str(run_dir),
            "--prompts_dir",
            str(prompts_dir),
            "--input",
            args.input,
        ]
        
        # Pass target_k for commands that need it
        if args.cmd in ("all", "aggregate"):
            cmd_args.extend(["--target_k", args.target_k])
        if args.target_k_exact:
            cmd_args.extend(["--target_k_exact", str(args.target_k_exact)])
        if args.model:
            cmd_args.extend(["--model", args.model])
        cmd_args.extend(["--n_taggers", str(args.n_taggers)])
        cmd_args.extend(["--consensus_mode", args.consensus_mode])
        cmd_args.extend(["--include_threshold", str(args.include_threshold)])
        cmd_args.extend(["--exclude_threshold", str(args.exclude_threshold)])
        if args.skip_stages:
            cmd_args.extend(["--skip_stages", args.skip_stages])
        
        cmd_args.append(args.cmd)
        run(cmd_args)


if __name__ == "__main__":
    main()

