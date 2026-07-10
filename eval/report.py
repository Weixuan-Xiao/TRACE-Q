"""Unified evaluation report over contract run directories.

Groups runs by (method, dataset, k_condition); per run computes quality (GDINA
fit + Qval + CA via R), structural checks, and expert-Q agreement (cached);
per group aggregates quality and computes 4-layer stability. Outputs
report.json, summary_quality.csv, summary_stability.csv, scatter.csv.
"""
import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_qmatrix import evaluate as eval_quality  # noqa: E402
from evaluate_stability import load_qmatrix  # noqa: E402
from eval.contract import discover_runs, load_run, validate_run  # noqa: E402
from eval.check_structure import check_structure  # noqa: E402
from eval.expert_agreement import aligned_agreement  # noqa: E402
from eval.stability import compute_stability  # noqa: E402

QUALITY_METRICS = [
    "AIC", "BIC", "CAIC", "SABIC", "RMSEA2", "SRMSR",
    "qval_modification_rate", "ca_test_level",
    "structural_n_errors", "expert_cell_agreement",
]


def evaluate_one_run(run_dir, dataset, expert, cache_dir, force=False):
    """Quality + structure + expert agreement for one run, cached as JSON."""
    run_dir = Path(run_dir)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{run_dir.name}.json"
    if cache_path.exists() and not force:
        with open(cache_path) as f:
            return json.load(f)

    run = load_run(run_dir)
    result = {"run_id": run["run_id"], "run_dir": str(run_dir)}

    quality = eval_quality(str(run_dir / "Q.csv"), dataset)
    result["quality"] = quality

    structure = check_structure(run["items"], run["skills"], run["matrix"])
    result["structure"] = structure

    if expert is not None:
        expert_skills, expert_matrix = expert
        result["expert_agreement"] = aligned_agreement(
            run["matrix"], expert_matrix, run["skills"], expert_skills)

    with open(cache_path, "w") as f:
        json.dump(result, f, indent=2)
    return result


def _flat_metrics(per_run_result):
    """Flatten one run's results into {metric: value} for aggregation."""
    out = {}
    quality = per_run_result.get("quality", {})
    for m in ("AIC", "BIC", "CAIC", "SABIC", "RMSEA2", "SRMSR",
              "qval_modification_rate", "ca_test_level"):
        v = quality.get(m)
        if isinstance(v, (int, float)):
            out[m] = v
    structure = per_run_result.get("structure", {})
    if "n_errors" in structure:
        out["structural_n_errors"] = structure["n_errors"]
    expert = per_run_result.get("expert_agreement")
    if expert and isinstance(expert.get("cell_agreement"), (int, float)):
        out["expert_cell_agreement"] = expert["cell_agreement"]
    return out


def _aggregate(per_run_metrics):
    """{metric: {mean, sd, min, max, n}} over a list of flat metric dicts."""
    agg = {}
    for metric in QUALITY_METRICS:
        values = [m[metric] for m in per_run_metrics if metric in m]
        if not values:
            continue
        agg[metric] = {
            "mean": round(statistics.mean(values), 4),
            "sd": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "n": len(values),
        }
    return agg


def main():
    parser = argparse.ArgumentParser(description="Unified evaluation report over contract runs.")
    parser.add_argument("--runs_root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--dataset", default="tatsuoka")
    parser.add_argument("--expert_q", default=None, help="Expert Q csv for agreement/ARI reference")
    parser.add_argument("--skip-embeddings", action="store_true")
    parser.add_argument("--skip-ari", action="store_true")
    parser.add_argument("--force", action="store_true", help="Ignore per-run cache")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_dirs = discover_runs(args.runs_root)
    if not run_dirs:
        print(f"No contract run dirs under {args.runs_root}")
        sys.exit(1)

    valid_dirs, invalid = [], []
    for rd in run_dirs:
        violations = validate_run(rd)
        if violations:
            invalid.append({"run_dir": str(rd), "violations": violations})
        else:
            valid_dirs.append(rd)
    if invalid:
        print(f"WARNING: {len(invalid)} invalid run dir(s) excluded (see report.json).")

    expert = None
    if args.expert_q:
        _e_items, e_skills, e_matrix = load_qmatrix(args.expert_q)
        expert = (e_skills, e_matrix)

    # Group by (method, dataset, k_condition)
    groups = {}
    for rd in valid_dirs:
        with open(rd / "config.json") as f:
            config = json.load(f)
        gid = f"{config['method']}|{config['dataset']}|{config['k_condition']}"
        groups.setdefault(gid, []).append(rd)

    report = {
        "config": {
            "runs_root": str(args.runs_root),
            "dataset": args.dataset,
            "expert_q": args.expert_q,
            "n_runs_total": len(run_dirs),
            "n_runs_valid": len(valid_dirs),
        },
        "invalid_runs": invalid,
        "groups": {},
    }

    for gid, rds in sorted(groups.items()):
        print(f"Group {gid}: {len(rds)} run(s)")
        per_run = []
        for rd in rds:
            print(f"  evaluating {rd.name} ...")
            per_run.append(evaluate_one_run(
                rd, args.dataset, expert, out_dir / "per_run", force=args.force))

        flat = [_flat_metrics(r) for r in per_run]
        stability = compute_stability(
            rds, out_dir / "stability" / gid.replace("|", "_"),
            dataset=args.dataset,
            skip_embeddings=args.skip_embeddings,
            skip_ari=args.skip_ari,
        )
        report["groups"][gid] = {
            "n_runs": len(rds),
            "quality": _aggregate(flat),
            "stability": stability,
            "runs": [r["run_id"] for r in per_run],
        }

    with open(out_dir / "report.json", "w") as f:
        json.dump(report, f, indent=2)

    # summary_quality.csv
    with open(out_dir / "summary_quality.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["group", "n_runs"] + [f"{m}_{s}" for m in QUALITY_METRICS for s in ("mean", "sd")])
        for gid, g in sorted(report["groups"].items()):
            row = [gid, g["n_runs"]]
            for m in QUALITY_METRICS:
                stats = g["quality"].get(m, {})
                row += [stats.get("mean"), stats.get("sd")]
            writer.writerow(row)

    # summary_stability.csv
    stab_cols = ["modal_k", "modal_k_fraction", "codebook_mean_sim",
                 "aligned_fleiss_kappa", "aligned_agreement", "aligned_item_perfect_rate",
                 "mean_ari", "min_ari"]
    with open(out_dir / "summary_stability.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["group", "n_runs"] + stab_cols)
        for gid, g in sorted(report["groups"].items()):
            s = g["stability"]
            k_layer = s.get("k_layer", {})
            cb = s.get("codebook_layer", {})
            mat = s.get("matrix_layer", {})
            aligned = mat.get("aligned", {}) if isinstance(mat, dict) else {}
            cls = s.get("classification_layer", {})
            writer.writerow([
                gid, s.get("n_runs"),
                k_layer.get("modal_k"), k_layer.get("modal_k_fraction"),
                cb.get("mean"),
                aligned.get("fleiss_kappa"), aligned.get("element_wise_agreement"),
                aligned.get("item_perfect_rate"),
                cls.get("mean_ari"), cls.get("min_ari"),
            ])

    # scatter.csv — one row per group: stability x, quality y candidates
    with open(out_dir / "scatter.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["group", "method", "dataset", "k_condition", "n_runs",
                         "stability_aligned_fleiss_kappa",
                         "RMSEA2_mean", "RMSEA2_sd", "SRMSR_mean", "SRMSR_sd",
                         "qval_modification_rate_mean", "qval_modification_rate_sd",
                         "ca_test_level_mean", "ca_test_level_sd",
                         "expert_cell_agreement_mean"])
        for gid, g in sorted(report["groups"].items()):
            method, dataset, k_condition = gid.split("|")
            aligned = g["stability"].get("matrix_layer", {}).get("aligned", {}) \
                if isinstance(g["stability"].get("matrix_layer"), dict) else {}
            q = g["quality"]
            writer.writerow([
                gid, method, dataset, k_condition, g["n_runs"],
                aligned.get("fleiss_kappa"),
                q.get("RMSEA2", {}).get("mean"), q.get("RMSEA2", {}).get("sd"),
                q.get("SRMSR", {}).get("mean"), q.get("SRMSR", {}).get("sd"),
                q.get("qval_modification_rate", {}).get("mean"),
                q.get("qval_modification_rate", {}).get("sd"),
                q.get("ca_test_level", {}).get("mean"), q.get("ca_test_level", {}).get("sd"),
                q.get("expert_cell_agreement", {}).get("mean"),
            ])

    print(f"Report written to: {out_dir}/report.json (+ summary_quality.csv, "
          f"summary_stability.csv, scatter.csv)")


if __name__ == "__main__":
    main()
