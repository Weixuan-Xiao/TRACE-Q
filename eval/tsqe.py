"""Data adjudication via TSQE (dimension C of the framework).

Estimates a data-driven Q with NPCDTools::TSQE at the method's K (cached per
dataset+K), then scores the method Q by aligned agreement with the TSQE Q.

Caveat (per spec): this metric is circular for the TSQE baseline itself
(agreement 1.0 by construction) and must not be used to rank that baseline.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_stability import load_qmatrix  # noqa: E402
from eval.expert_agreement import aligned_agreement  # noqa: E402

_EVAL_DIR = Path(__file__).resolve().parent


def tsqe_q_for(dataset, k, cache_dir):
    """Compute (or reuse cached) TSQE Q for a dataset at K=k. Returns CSV path."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe_dataset = str(dataset).replace("/", "_")
    out_path = cache_dir / f"tsqe_{safe_dataset}_K{k}.csv"
    if out_path.exists():
        return out_path
    cmd = [
        "Rscript", str(_EVAL_DIR / "tsqe.R"),
        "--dataset", str(dataset), "--k", str(k), "--output", str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out_path.exists():
        raise RuntimeError(f"TSQE failed for {dataset} K={k}: {proc.stdout} {proc.stderr}")
    return out_path


def tsqe_agreement(matrix, skills, dataset, cache_dir):
    """Aligned agreement between a method Q (as matrix) and the TSQE Q at the same K."""
    tsqe_path = tsqe_q_for(dataset, len(skills), cache_dir)
    _t_items, t_skills, t_matrix = load_qmatrix(tsqe_path)
    result = aligned_agreement(matrix, t_matrix, skills, t_skills)
    result["tsqe_q_path"] = str(tsqe_path)
    return result


def main():
    parser = argparse.ArgumentParser(description="Aligned agreement between method Q and TSQE Q.")
    parser.add_argument("--qmatrix", required=True)
    parser.add_argument("--dataset", default="tatsuoka")
    parser.add_argument("--cache_dir", default="eval_out/tsqe")
    args = parser.parse_args()

    _items, skills, matrix = load_qmatrix(args.qmatrix)
    result = tsqe_agreement(matrix, skills, args.dataset, args.cache_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
