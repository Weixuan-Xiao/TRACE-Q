"""V1: metric sensitivity simulation (framework section 5).

Corrupt the expert Q at increasing rates; verify every quality metric degrades
monotonically with corruption. Validates the evaluation framework itself.
"""
import argparse
import csv
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_qmatrix import evaluate as eval_quality  # noqa: E402
from evaluate_stability import load_qmatrix  # noqa: E402
from eval.check_structure import check_structure  # noqa: E402
from eval.expert_agreement import aligned_agreement  # noqa: E402

# Direction each metric moves as the Q-matrix gets worse.
METRIC_DIRECTIONS = {
    "AIC": "up", "BIC": "up", "CAIC": "up", "SABIC": "up",
    "RMSEA2": "up", "SRMSR": "up",
    "qval_modification_rate": "up",
    "ca_test_level": "down",
    "expert_cell_agreement": "down",
}


def corrupt(matrix, rate, rng, max_tries=1000):
    """Density-preserving corruption: flip round(rate*cells) cells, half 1->0
    and half 0->1, avoiding all-zero rows/cols.

    Balanced flips isolate "wrong placement" from Q-density: under saturated
    G-DINA, simply adding 1s increases item parameter counts and can *improve*
    fit, so unbalanced random flips would confound corruption with density.

    Returns (corrupted_matrix, n_resamples).
    """
    n_items = len(matrix)
    n_skills = len(matrix[0])
    n_cells = n_items * n_skills
    n_flips = round(rate * n_cells)
    n_flips -= n_flips % 2  # even count so density is exactly preserved
    if n_flips == 0:
        return [row[:] for row in matrix], 0

    one_cells = [(i, j) for i in range(n_items) for j in range(n_skills) if matrix[i][j] == 1]
    zero_cells = [(i, j) for i in range(n_items) for j in range(n_skills) if matrix[i][j] == 0]
    half = n_flips // 2
    if half > len(one_cells) or half > len(zero_cells):
        raise ValueError(f"rate {rate} needs {half} flips per side; "
                         f"matrix has {len(one_cells)} ones / {len(zero_cells)} zeros")

    for attempt in range(max_tries):
        flips = rng.sample(one_cells, half) + rng.sample(zero_cells, half)
        corrupted = [row[:] for row in matrix]
        for i, j in flips:
            corrupted[i][j] = 1 - corrupted[i][j]
        row_ok = all(sum(row) > 0 for row in corrupted)
        col_ok = all(any(corrupted[i][j] for i in range(n_items)) for j in range(n_skills))
        if row_ok and col_ok:
            return corrupted, attempt
    raise RuntimeError(f"could not corrupt without all-zero row/col after {max_tries} tries")


def _write_q(items, skills, matrix, path):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id"] + list(skills))
        for item_id, row in zip(items, matrix):
            writer.writerow([item_id] + list(row))


def check_monotonicity(per_rate_means):
    """per_rate_means: {metric: [(rate, mean), ...]} sorted by rate (rate 0 included).

    Returns {metric: {"direction", "values", "monotone"}}.
    """
    verdicts = {}
    for metric, series in per_rate_means.items():
        direction = METRIC_DIRECTIONS.get(metric)
        if direction is None or len(series) < 2:
            continue
        values = [v for _r, v in series]
        if direction == "up":
            monotone = all(values[i] <= values[i + 1] for i in range(len(values) - 1))
        else:
            monotone = all(values[i] >= values[i + 1] for i in range(len(values) - 1))
        verdicts[metric] = {
            "direction": direction,
            "rates": [r for r, _v in series],
            "means": [round(v, 4) for v in values],
            "monotone": monotone,
        }
    return verdicts


def main():
    parser = argparse.ArgumentParser(description="V1 metric sensitivity simulation.")
    parser.add_argument("--expert_q", default="data/expert_q_tatsuoka.csv")
    parser.add_argument("--rates", default="0.05,0.10,0.20")
    parser.add_argument("--replicates", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dataset", default="tatsuoka")
    parser.add_argument("--out", default="eval_out/v1")
    args = parser.parse_args()

    rates = [float(r) for r in args.rates.split(",")]
    rng = random.Random(args.seed)
    out_dir = Path(args.out)
    corrupted_dir = out_dir / "corrupted"
    corrupted_dir.mkdir(parents=True, exist_ok=True)

    items, skills, expert_matrix = load_qmatrix(args.expert_q)

    conditions = [(0.0, 0)]  # baseline: uncorrupted expert Q, single instance
    for rate in rates:
        for rep in range(args.replicates):
            conditions.append((rate, rep))

    rows = []
    for rate, rep in conditions:
        if rate == 0.0:
            matrix, n_resamples = [row[:] for row in expert_matrix], 0
            q_path = Path(args.expert_q)
        else:
            matrix, n_resamples = corrupt(expert_matrix, rate, rng)
            q_path = corrupted_dir / f"q_rate{rate}_rep{rep}.csv"
            _write_q(items, skills, matrix, q_path)

        print(f"rate={rate} rep={rep}: fitting GDINA ...", flush=True)
        quality = eval_quality(str(q_path), args.dataset)
        structure = check_structure(items, skills, matrix)
        agreement = aligned_agreement(matrix, expert_matrix)

        row = {"rate": rate, "rep": rep, "n_resamples": n_resamples,
               "structural_n_errors": structure["n_errors"],
               "expert_cell_agreement": agreement["cell_agreement"]}
        for m in ("AIC", "BIC", "CAIC", "SABIC", "RMSEA2", "SRMSR",
                  "qval_modification_rate", "ca_test_level"):
            v = quality.get(m)
            row[m] = v if isinstance(v, (int, float)) else None
        row["converged"] = quality.get("converged")
        rows.append(row)

    # aggregate per rate
    all_rates = [0.0] + rates
    per_rate_means = {}
    for metric in METRIC_DIRECTIONS:
        series = []
        for rate in all_rates:
            values = [r[metric] for r in rows if r["rate"] == rate and r.get(metric) is not None]
            if values:
                series.append((rate, statistics.mean(values)))
        if len(series) >= 2:
            per_rate_means[metric] = series

    verdicts = check_monotonicity(per_rate_means)

    with open(out_dir / "v1_metrics.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "config": {"expert_q": args.expert_q, "rates": rates,
                   "replicates": args.replicates, "seed": args.seed,
                   "dataset": args.dataset},
        "n_fits": len(rows),
        "monotonicity": verdicts,
        "all_monotone": all(v["monotone"] for v in verdicts.values()),
    }
    with open(out_dir / "v1_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print()
    for metric, v in verdicts.items():
        status = "PASS" if v["monotone"] else "FAIL"
        print(f"{status}  {metric:<26} ({v['direction']:>4}): {v['means']}")
    print(f"\nOverall: {'PASS' if report['all_monotone'] else 'FAIL'}")
    print(f"Report written to: {out_dir}/v1_report.json")


if __name__ == "__main__":
    main()
