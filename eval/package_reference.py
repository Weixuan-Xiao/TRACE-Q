"""Package reference Q-matrices (expert Q, TSQE Q) as contract run directories.

Both are single deterministic instances (constant reference lines in plots).
Circularity: expert-agreement must not rank the expert run; TSQE-agreement
must not rank the tsqe run (framework section 4).
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_stability import load_qmatrix  # noqa: E402
from eval.contract import validate_run  # noqa: E402
from eval.convert_legacy import _write_canonical_q  # noqa: E402
from eval.tsqe import tsqe_q_for  # noqa: E402


def package_q(q_csv, method, k_condition, out_dir, dataset):
    items, skills, matrix = load_qmatrix(q_csv)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_canonical_q(items, skills, matrix, out_dir / "Q.csv")
    config = {
        "method": method,
        "dataset": dataset,
        "k_condition": k_condition,
        "k_selected": len(skills),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "method_version": None,
        "model": None,
        "provider": None,
        "seed": None,
        "token_cost": None,
        "source": {"reference_csv": str(q_csv)},
    }
    with open(out_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)
    return validate_run(out_dir)


def main():
    parser = argparse.ArgumentParser(description="Package expert and TSQE reference Qs.")
    parser.add_argument("--out", required=True, help="Runs root for reference dirs")
    parser.add_argument("--dataset", default="tatsuoka")
    parser.add_argument("--expert_q", default="data/expert_q_tatsuoka.csv")
    parser.add_argument("--tsqe_k", default="auto",
                        help="'auto' = BIC-optimal K over 3-8 sweep, or an integer")
    parser.add_argument("--tsqe_cache", default="eval_out/tsqe")
    args = parser.parse_args()

    jobs = []
    expert_path = Path(args.expert_q)
    _e_items, e_skills, _e_m = load_qmatrix(expert_path)
    jobs.append((expert_path, "expert", f"fixed_{len(e_skills)}", "expert_run1"))

    tsqe_path = tsqe_q_for(args.dataset, args.tsqe_k, args.tsqe_cache)
    tsqe_condition = "auto" if args.tsqe_k == "auto" else f"fixed_{args.tsqe_k}"
    jobs.append((tsqe_path, "tsqe", tsqe_condition, "tsqe_run1"))

    any_bad = False
    for q_csv, method, k_condition, dirname in jobs:
        out_dir = Path(args.out) / dirname
        violations = package_q(q_csv, method, k_condition, out_dir, args.dataset)
        status = "OK" if not violations else f"INVALID {violations}"
        print(f"{status:8} {method} ({k_condition}) -> {out_dir}")
        any_bad |= bool(violations)
    sys.exit(1 if any_bad else 0)


if __name__ == "__main__":
    main()
