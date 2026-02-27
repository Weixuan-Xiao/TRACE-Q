"""Stability metrics for Q-matrices across repeated runs."""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path


def load_qmatrix(csv_path):
    """Load Q-matrix CSV -> (item_ids, skill_ids, matrix[row][col])."""
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        skill_cols = [h for h in header[1:] if h.startswith("S")]
        n_skills = len(skill_cols)
        items, rows = [], []
        for row in reader:
            items.append(row[0])
            rows.append([int(row[1 + c].replace("*", "").strip()) for c in range(n_skills)])
    return items, skill_cols, rows


def fleiss_kappa(all_matrices, n_runs):
    """Fleiss' kappa: each run = a rater, each cell = a subject."""
    n_items = len(all_matrices[0])
    n_skills = len(all_matrices[0][0])
    N = n_items * n_skills

    count_1 = [0] * N
    for mat in all_matrices:
        idx = 0
        for i in range(n_items):
            for j in range(n_skills):
                count_1[idx] += mat[i][j]
                idx += 1

    sum_Pi = 0.0
    for s in range(N):
        c1 = count_1[s]
        c0 = n_runs - c1
        sum_Pi += (c0 * (c0 - 1) + c1 * (c1 - 1)) / (n_runs * (n_runs - 1))
    P_bar = sum_Pi / N

    total = N * n_runs
    p1 = sum(count_1) / total
    p0 = 1 - p1
    P_e = p0 * p0 + p1 * p1

    if P_e >= 1.0:
        return 1.0
    return (P_bar - P_e) / (1 - P_e)


def element_wise_agreement(all_matrices, n_runs):
    """Average cell-level agreement with majority vote."""
    n_items = len(all_matrices[0])
    n_skills = len(all_matrices[0][0])
    total_agreement = 0.0
    total_cells = n_items * n_skills

    for i in range(n_items):
        for j in range(n_skills):
            ones = sum(mat[i][j] for mat in all_matrices)
            majority_count = max(ones, n_runs - ones)
            total_agreement += majority_count / n_runs

    return total_agreement / total_cells


def compute_stability_metrics(run_dir: str, k: int) -> dict:
    """
    Compute stability metrics across all runs in a directory.

    Expects: run_dir/run1/step6_Q_matrix_K{k}.csv, run_dir/run2/..., etc.
    Falls back to step8_auditor_Q_matrix_K{k}_reviewed.csv if step6 not found.
    """
    run_dir = Path(run_dir)
    run_dirs = sorted(
        [d for d in run_dir.iterdir() if d.is_dir() and d.name.startswith("run")],
        key=lambda p: int(p.name.removeprefix("run")),
    )

    all_matrices = []
    for rd in run_dirs:
        qm_path = rd / f"step6_Q_matrix_K{k}.csv"
        if not qm_path.exists():
            qm_path = rd / f"step8_auditor_Q_matrix_K{k}_reviewed.csv"
        if qm_path.exists():
            _, _, matrix = load_qmatrix(qm_path)
            all_matrices.append(matrix)

    n_runs = len(all_matrices)
    if n_runs < 2:
        return {"error": f"Need >= 2 runs, found {n_runs}", "n_runs": n_runs}

    n_items = len(all_matrices[0])
    n_skills = len(all_matrices[0][0])

    q_strings = [str(mat) for mat in all_matrices]
    unique_counts = Counter(q_strings)
    n_unique = len(unique_counts)
    modal_freq = unique_counts.most_common(1)[0][1]

    return {
        "run_dir": str(run_dir),
        "k": k,
        "n_runs": n_runs,
        "n_items": n_items,
        "n_skills": n_skills,
        "total_cells": n_items * n_skills,
        "element_wise_agreement": round(element_wise_agreement(all_matrices, n_runs), 4),
        "fleiss_kappa": round(fleiss_kappa(all_matrices, n_runs), 4),
        "n_unique_qmatrices": n_unique,
        "modal_qmatrix_frequency": modal_freq,
        "modal_qmatrix_frequency_pct": round(modal_freq / n_runs, 4),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute stability metrics across runs.")
    parser.add_argument("--run_dir", required=True, help="Directory containing run1/, run2/, ...")
    parser.add_argument("--k", type=int, required=True, help="K value of Q-matrices to analyze")
    parser.add_argument("--output", default=None, help="Output JSON path (default: print to stdout)")
    args = parser.parse_args()

    result = compute_stability_metrics(args.run_dir, args.k)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Stability metrics written to: {args.output}")
    else:
        print(json.dumps(result, indent=2))
