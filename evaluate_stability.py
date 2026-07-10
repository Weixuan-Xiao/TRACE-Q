"""Stability metrics for Q-matrices across repeated runs."""
import argparse
import csv
import json
import sys
from collections import Counter
from itertools import permutations
from pathlib import Path

_META_COLS = {"item_id", "audit_verdict", "audit_note"}


def load_qmatrix(csv_path):
    """Load Q-matrix CSV -> (item_ids, skill_ids, matrix[row][col]).

    Skill columns are all columns after item_id that are not known metadata.
    Works with any skill-ID prefix (S01, M01, etc.).
    """
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        skill_cols = [h for h in header[1:] if h not in _META_COLS]
        col_indices = [header.index(h) for h in skill_cols]
        items, rows = [], []
        for row in reader:
            items.append(row[0])
            rows.append([int(row[c].replace("*", "").strip()) for c in col_indices])
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


def item_perfect_rate(all_matrices):
    """Fraction of items whose full row is identical across all runs."""
    n_items = len(all_matrices[0])
    perfect = 0
    for i in range(n_items):
        rows = {tuple(mat[i]) for mat in all_matrices}
        if len(rows) == 1:
            perfect += 1
    return perfect / n_items


def _count_agreement(mat_a, mat_b):
    """Count matching cells between two equal-sized matrices."""
    total = 0
    for row_a, row_b in zip(mat_a, mat_b):
        for a, b in zip(row_a, row_b):
            total += (a == b)
    return total


def _apply_col_permutation(matrix, perm):
    """Return a new matrix with columns reordered by *perm*."""
    return [[row[p] for p in perm] for row in matrix]


def _best_permutation(reference, target):
    """Find the column permutation of *target* that maximises agreement
    with *reference*.  Returns (permuted_matrix, best_perm_tuple)."""
    n_skills = len(reference[0])
    best_score, best_perm = -1, None
    for perm in permutations(range(n_skills)):
        permuted = _apply_col_permutation(target, perm)
        score = _count_agreement(reference, permuted)
        if score > best_score:
            best_score, best_perm = score, perm
    return _apply_col_permutation(target, best_perm), best_perm


def _pick_reference(all_matrices):
    """Choose the matrix with highest average agreement to all others
    (before alignment) as the reference — more robust than always picking
    the first run."""
    best_idx, best_total = 0, -1
    for i, mi in enumerate(all_matrices):
        total = sum(_count_agreement(mi, mj) for j, mj in enumerate(all_matrices) if j != i)
        if total > best_total:
            best_total, best_idx = total, i
    return best_idx


def align_matrices(all_matrices):
    """Align all Q-matrices via best column permutation to a reference.

    Returns (aligned_matrices, ref_index, permutations_used).
    Feasible for K ≤ 8 (8! = 40 320 permutations).
    """
    ref_idx = _pick_reference(all_matrices)
    ref = all_matrices[ref_idx]
    aligned, perms = [], []
    for i, mat in enumerate(all_matrices):
        if i == ref_idx:
            aligned.append(mat)
            perms.append(tuple(range(len(ref[0]))))
        else:
            aligned_mat, perm = _best_permutation(ref, mat)
            aligned.append(aligned_mat)
            perms.append(perm)
    return aligned, ref_idx, perms


def compute_stability_from_matrices(all_matrices, align: bool = True) -> dict:
    """
    Compute stability metrics over a list of equal-shaped Q-matrices.

    If *align* is True (default), columns are permutation-aligned before
    computing metrics so that differently-ordered but conceptually equivalent
    skill columns are matched up.  Raw (unaligned) metrics are also reported.
    """
    n_runs = len(all_matrices)
    if n_runs < 2:
        return {"error": f"Need >= 2 runs, found {n_runs}", "n_runs": n_runs}

    n_items = len(all_matrices[0])
    n_skills = len(all_matrices[0][0])

    raw_agreement = round(element_wise_agreement(all_matrices, n_runs), 4)
    raw_kappa = round(fleiss_kappa(all_matrices, n_runs), 4)

    q_strings = [str(mat) for mat in all_matrices]
    unique_counts = Counter(q_strings)
    n_unique = len(unique_counts)
    modal_freq = unique_counts.most_common(1)[0][1]

    result = {
        "n_runs": n_runs,
        "n_items": n_items,
        "n_skills": n_skills,
        "total_cells": n_items * n_skills,
        "element_wise_agreement": raw_agreement,
        "fleiss_kappa": raw_kappa,
        "item_perfect_rate": round(item_perfect_rate(all_matrices), 4),
        "n_unique_qmatrices": n_unique,
        "modal_qmatrix_frequency": modal_freq,
        "modal_qmatrix_frequency_pct": round(modal_freq / n_runs, 4),
    }

    if align and n_skills <= 8:
        aligned, ref_idx, perms = align_matrices(all_matrices)
        aligned_agreement = round(element_wise_agreement(aligned, n_runs), 4)
        aligned_kappa = round(fleiss_kappa(aligned, n_runs), 4)

        aq_strings = [str(mat) for mat in aligned]
        a_unique_counts = Counter(aq_strings)
        a_n_unique = len(a_unique_counts)
        a_modal_freq = a_unique_counts.most_common(1)[0][1]

        result["aligned"] = {
            "element_wise_agreement": aligned_agreement,
            "fleiss_kappa": aligned_kappa,
            "item_perfect_rate": round(item_perfect_rate(aligned), 4),
            "reference_run": ref_idx + 1,
            "permutations_used": [list(p) for p in perms],
            "n_unique_qmatrices": a_n_unique,
            "modal_qmatrix_frequency": a_modal_freq,
            "modal_qmatrix_frequency_pct": round(a_modal_freq / n_runs, 4),
        }

    return result


def compute_stability_metrics(run_dir: str, k: int, align: bool = True) -> dict:
    """
    Compute stability metrics across all runs in a directory (legacy layout).

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

    result = compute_stability_from_matrices(all_matrices, align=align)
    result = {"run_dir": str(run_dir), "k": k, **result}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute stability metrics across runs.")
    parser.add_argument("--run_dir", required=True, help="Directory containing run1/, run2/, ...")
    parser.add_argument("--k", type=int, required=True, help="K value of Q-matrices to analyze")
    parser.add_argument("--no-align", action="store_true",
                        help="Skip column-permutation alignment (report raw metrics only)")
    parser.add_argument("--output", default=None, help="Output JSON path (default: print to stdout)")
    args = parser.parse_args()

    result = compute_stability_metrics(args.run_dir, args.k, align=not args.no_align)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Stability metrics written to: {args.output}")
    else:
        print(json.dumps(result, indent=2))
