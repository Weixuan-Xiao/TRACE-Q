"""Evaluate one baseline without pooling different models."""

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from eval.contract import load_run, validate_run
from eval.report import _flat_metrics
from eval.stability import compute_stability


def stats(values):
    values = [v for v in values if isinstance(v, (int, float))]
    if not values:
        return None
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 4),
        "sd": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", default="baseline_evaluation/runs")
    parser.add_argument("--run-glob", default="b1_naive_*_auto_run*")
    parser.add_argument("--scope-label", default="B1")
    parser.add_argument("--file-prefix", default="b1")
    parser.add_argument("--per-run", default="baseline_evaluation/report/per_run")
    parser.add_argument("--out", default="baseline_evaluation/b1_analysis")
    parser.add_argument("--codebook-stability", default="baseline_evaluation/b1_analysis/codebook_stability.json")
    parser.add_argument("--skip-ari", action="store_true")
    args = parser.parse_args()

    runs_root = Path(args.runs_root)
    cache_root = Path(args.per_run)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    grouped = defaultdict(list)
    invalid = []
    rows = []
    for run_dir in sorted(runs_root.glob(args.run_glob)):
        violations = validate_run(run_dir)
        cache_path = cache_root / f"{run_dir.name}.json"
        if violations or not cache_path.exists():
            invalid.append({
                "run_id": run_dir.name,
                "violations": violations or ["missing per-run evaluation cache"],
            })
            continue
        run = load_run(run_dir)
        result = json.loads(cache_path.read_text())
        config = run["config"]
        model = config["model"]
        grouped[model].append(run_dir)
        flat = _flat_metrics(result)
        token_cost = config.get("token_cost", {})
        row = {
            "run_id": run_dir.name,
            "model": model,
            "provider": config.get("provider"),
            "k": config["k_selected"],
            "input_tokens": token_cost.get("input"),
            "output_tokens": token_cost.get("output"),
            "total_tokens": sum(v or 0 for v in (token_cost.get("input"), token_cost.get("output"))),
            "calls": token_cost.get("calls"),
            "converged": result.get("quality", {}).get("converged"),
            "structural_warnings": result.get("structure", {}).get("n_warnings"),
            "density": result.get("structure", {}).get("density"),
            "stale_failed_marker": (run_dir / "FAILED.txt").exists(),
            **flat,
        }
        rows.append(row)

    metric_names = [
        "tsqe_cell_agreement", "expert_cell_agreement", "structural_n_errors",
        "structural_warnings", "density", "total_tokens", "input_tokens",
        "output_tokens", "AIC", "BIC", "RMSEA2", "SRMSR",
    ]
    model_summary = {}
    quality_by_model_k = {}
    for model, run_dirs in sorted(grouped.items()):
        model_rows = [r for r in rows if r["model"] == model]
        k_counts = Counter(r["k"] for r in model_rows)
        stability = compute_stability(
            run_dirs,
            out / "stability" / model.replace("/", "_"),
            skip_embeddings=True,
            skip_ari=args.skip_ari,
        )
        model_summary[model] = {
            "n_runs": len(model_rows),
            "k_distribution": {str(k): k_counts[k] for k in sorted(k_counts)},
            "converged": sum(r["converged"] is True for r in model_rows),
            "stale_failed_markers": sum(r["stale_failed_marker"] for r in model_rows),
            "metrics": {m: stats([r.get(m) for r in model_rows]) for m in metric_names},
            "stability": stability,
        }
        for k in sorted(k_counts):
            subset = [r for r in model_rows if r["k"] == k]
            quality_by_model_k[f"{model}|K={k}"] = {
                "n_runs": len(subset),
                "fit_metrics": {m: stats([r.get(m) for r in subset]) for m in ("AIC", "BIC", "RMSEA2", "SRMSR")},
            }

    codebook_path = Path(args.codebook_stability)
    report = {
        "scope": f"{args.scope_label} only; models evaluated separately",
        "n_runs_found": len(rows) + len(invalid),
        "n_runs_valid": len(rows),
        "invalid_runs": invalid,
        "codebook_stability": json.loads(codebook_path.read_text()) if codebook_path.exists() else {
            "status": "pending canonical-skill annotation"
        },
        "model_summary": model_summary,
        "quality_by_model_k": quality_by_model_k,
    }
    analysis_path = out / f"{args.file_prefix}_analysis.json"
    run_level_path = out / f"{args.file_prefix}_run_level.csv"
    analysis_path.write_text(json.dumps(report, indent=2))

    columns = list(dict.fromkeys(key for row in rows for key in row))
    with run_level_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(report, indent=2))
    print(f"Wrote {analysis_path} and {run_level_path}")


if __name__ == "__main__":
    main()
