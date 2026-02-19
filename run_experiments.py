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
        # For audit-only runs, target_k is not needed (audit discovers files)
        
        cmd_args.append(args.cmd)
        run(cmd_args)


if __name__ == "__main__":
    main()

