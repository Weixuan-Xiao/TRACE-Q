"""Master evaluation: quality (G-DINA fit) + stability across runs."""
import argparse
import json
import statistics
from pathlib import Path

from evaluate_qmatrix import evaluate as eval_quality
from evaluate_stability import compute_stability_metrics


def evaluate_experiment(run_dir: str, k: int, dataset: str = "tatsuoka") -> dict:
    """Run quality + stability evaluation on a set of repeated runs."""
    run_dir = Path(run_dir)
    run_dirs = sorted(
        [d for d in run_dir.iterdir() if d.is_dir() and d.name.startswith("run")],
        key=lambda p: int(p.name.removeprefix("run")),
    )

    # --- Quality: evaluate each run's Q-matrix ---
    quality_results = []
    for rd in run_dirs:
        qm_path = rd / f"step6_Q_matrix_K{k}.csv"
        if not qm_path.exists():
            qm_path = rd / f"step8_auditor_Q_matrix_K{k}_reviewed.csv"
        if qm_path.exists():
            q_eval = eval_quality(str(qm_path), dataset)
            if q_eval.get("error") is None:
                quality_results.append(q_eval)

    # Aggregate quality metrics: mean +/- SD
    quality_summary = {}
    for metric in ["AIC", "BIC", "CAIC", "SABIC", "RMSEA2", "SRMSR"]:
        values = [r[metric] for r in quality_results if r.get(metric) is not None]
        if values:
            quality_summary[metric] = {
                "mean": round(statistics.mean(values), 4),
                "sd": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "n": len(values),
            }

    # --- Stability ---
    stability = compute_stability_metrics(str(run_dir), k)

    return {
        "config": {
            "run_dir": str(run_dir),
            "k": k,
            "dataset": dataset,
            "n_runs_evaluated": len(quality_results),
        },
        "quality": quality_summary,
        "stability": stability,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--dataset", default="tatsuoka")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    result = evaluate_experiment(args.run_dir, args.k, args.dataset)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Report written to: {args.output}")
    else:
        print(json.dumps(result, indent=2))
