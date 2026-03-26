"""analyze_stability.py — Cross-run stability analysis for the Q-matrix pipeline.

Compares pre-audit (step6) and post-audit (step8) Q-matrices across runs.
Skill columns are permutation-aligned before computing metrics so that
semantically equivalent codebooks with different column orderings match.
When both stages are analysed, permutations from step6 are reused for step8.

Step8 data cleaning: auditor annotations (``*`` on modified cells) and
metadata columns (``audit_verdict``, ``audit_note``) are stripped automatically.

Usage
-----
    python analyze_stability.py [BASE_DIR] [TARGET_K] [--stage {step6,step8,both}]

Examples
--------
    python analyze_stability.py outputs_exp/v2              # auto K, both stages
    python analyze_stability.py outputs_exp/v2 5            # force K=5
    python analyze_stability.py outputs_exp/v2 --stage step8
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from itertools import combinations, permutations
from pathlib import Path


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

_META_COLS = {"item_id", "audit_verdict", "audit_note"}


def _load_qmatrix(csv_path: Path) -> tuple[list[str], list[str], list[list[int]]]:
    """Load a Q-matrix CSV → (item_ids, skill_ids, matrix[row][col])."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        skill_cols = [h for h in header[1:] if h not in _META_COLS]
        col_indices = [header.index(h) for h in skill_cols]
        items: list[str] = []
        rows: list[list[int]] = []
        for row in reader:
            items.append(row[0])
            rows.append([int(row[c].rstrip("*")) for c in col_indices])
    return items, skill_cols, rows


def _load_codebook(json_path: Path) -> list[dict]:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("skills") or data.get("codebook") or data.get("final_codebook", [])


# ---------------------------------------------------------------------------
# Permutation alignment
# ---------------------------------------------------------------------------

def _find_best_permutation(
    ref_mat: list[list[int]], other_mat: list[list[int]],
) -> tuple[tuple[int, ...], int]:
    """Find the column permutation of *other_mat* minimising Hamming to *ref_mat*.

    Feasible for K <= 8 (8! = 40 320 permutations).
    """
    n_items = len(ref_mat)
    n_skills = len(ref_mat[0])
    identity = tuple(range(n_skills))

    best_h = sum(
        ref_mat[i][j] != other_mat[i][j]
        for i in range(n_items)
        for j in range(n_skills)
    )
    best_perm = identity
    if best_h == 0:
        return best_perm, 0

    for perm in permutations(range(n_skills)):
        if perm == identity:
            continue
        h = 0
        for i in range(n_items):
            for j in range(n_skills):
                if ref_mat[i][j] != other_mat[i][perm[j]]:
                    h += 1
                    if h >= best_h:
                        break
            if h >= best_h:
                break
        if h < best_h:
            best_h = h
            best_perm = perm
            if best_h == 0:
                break

    return best_perm, best_h


def _apply_perm(mat: list[list[int]], perm: tuple[int, ...]) -> list[list[int]]:
    k = len(perm)
    return [[row[perm[j]] for j in range(k)] for row in mat]


def _align_matrices(
    all_mats: list[list[list[int]]],
) -> tuple[list[list[list[int]]], list[tuple[int, ...]]]:
    """Align every matrix to the first via optimal column permutation."""
    if not all_mats:
        return [], []
    n_skills = len(all_mats[0][0])
    identity = tuple(range(n_skills))
    if len(all_mats) == 1:
        return list(all_mats), [identity]

    ref = all_mats[0]
    perms: list[tuple[int, ...]] = [identity]
    aligned: list[list[list[int]]] = [ref]
    for mat in all_mats[1:]:
        perm, _ = _find_best_permutation(ref, mat)
        perms.append(perm)
        aligned.append(_apply_perm(mat, perm))
    return aligned, perms


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _cohens_kappa(v1: list[int], v2: list[int]) -> float:
    n = len(v1)
    if n == 0:
        return 1.0
    agree = sum(a == b for a, b in zip(v1, v2))
    po = agree / n
    mean1 = sum(v1) / n
    mean2 = sum(v2) / n
    pe = mean1 * mean2 + (1 - mean1) * (1 - mean2)
    if pe >= 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def _analyze_stage(
    all_mats: list[list[list[int]]],
    ref_items: list[str],
    run_names: list[str],
) -> dict:
    """Compute stability metrics for one stage. Returns a metrics dict."""
    n_runs = len(all_mats)
    n_items = len(ref_items)
    n_skills = len(all_mats[0][0])
    total_cells = n_items * n_skills

    # Element-wise agreement: fraction of runs agreeing with the majority value
    vote_sums = [[0] * n_skills for _ in range(n_items)]
    for mat in all_mats:
        for i in range(n_items):
            for j in range(n_skills):
                vote_sums[i][j] += mat[i][j]

    perfect_cells = 0
    agree_total = 0.0
    for i in range(n_items):
        for j in range(n_skills):
            majority = vote_sums[i][j] / n_runs
            cell_agree = max(majority, 1 - majority)
            agree_total += cell_agree
            if cell_agree == 1.0:
                perfect_cells += 1
    overall_agree = agree_total / total_cells

    # Item-level perfect agreement
    item_perfect = sum(
        1 for i in range(n_items)
        if len(set(tuple(mat[i]) for mat in all_mats)) == 1
    )

    # Whole-matrix perfect agreement
    mat_sigs = Counter(tuple(tuple(row) for row in mat) for mat in all_mats)
    perfect_qmatrix = mat_sigs.most_common(1)[0][1]

    # Pairwise Cohen's Kappa
    kappa_list: list[float] = []
    for (i1, _), (i2, _) in combinations(enumerate(run_names), 2):
        flat1 = [all_mats[i1][i][j] for i in range(n_items) for j in range(n_skills)]
        flat2 = [all_mats[i2][i][j] for i in range(n_items) for j in range(n_skills)]
        kappa_list.append(_cohens_kappa(flat1, flat2))

    return {
        "n_runs": n_runs,
        "overall_agree": overall_agree,
        "perfect_cells": perfect_cells,
        "total_cells": total_cells,
        "item_perfect_rate": item_perfect / n_items,
        "perfect_qmatrix": perfect_qmatrix,
        "avg_kappa": sum(kappa_list) / len(kappa_list),
        "min_kappa": min(kappa_list),
    }


# ---------------------------------------------------------------------------
# Stage loading
# ---------------------------------------------------------------------------

def _load_stage_matrices(
    run_dirs: list[Path], target_k: int, stage: str,
) -> dict[str, tuple[list[str], list[str], list[list[int]]]]:
    matrices: dict[str, tuple[list[str], list[str], list[list[int]]]] = {}
    for rd in run_dirs:
        if stage == "step6":
            qm_path = rd / f"step6_Q_matrix_K{target_k}.csv"
        else:
            qm_path = rd / f"step8_auditor_Q_matrix_K{target_k}_reviewed.csv"
        if qm_path.exists():
            matrices[rd.name] = _load_qmatrix(qm_path)
    return matrices


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cross-run stability analysis for Q-matrix pipeline.",
    )
    parser.add_argument("base_dir", nargs="?", default="outputs_exp/v2",
                        help="Base directory containing run* folders.")
    parser.add_argument("target_k", nargs="?", type=int, default=None,
                        help="K level to analyze (auto-detected if omitted).")
    parser.add_argument("--stage", choices=["step6", "step8", "both"],
                        default="both",
                        help="step6 (pre-audit), step8 (post-audit), or both.")
    args = parser.parse_args()

    base = Path(args.base_dir)
    target_k: int | None = args.target_k

    # Discover runs
    run_dirs = sorted(
        [d for d in base.iterdir() if d.is_dir() and d.name.startswith("run")],
        key=lambda p: int(p.name.removeprefix("run")),
    )
    print(f"Found {len(run_dirs)} runs: {[d.name for d in run_dirs]}\n")
    if len(run_dirs) < 2:
        print("Need at least 2 runs for stability analysis.")
        return

    # K consistency
    k_values: dict[str, int] = {}
    for rd in run_dirs:
        cb_path = rd / "step3_skill_codebook.json"
        if cb_path.exists():
            k_values[rd.name] = len(_load_codebook(cb_path))
    if not k_values:
        print("No codebooks found. Aborting.")
        return
    counts = Counter(k_values.values())
    most_common_k, k_freq = counts.most_common(1)[0]
    if target_k is None:
        target_k = most_common_k
    print(f"Analyzing K = {target_k}  (K consistency: {k_freq}/{len(k_values)})\n")

    # Process stages
    stages = ["step6", "step8"] if args.stage == "both" else [args.stage]
    results: dict[str, dict] = {}
    shared_perms: dict[str, tuple[int, ...]] | None = None

    for stg in stages:
        matrices = _load_stage_matrices(run_dirs, target_k, stg)
        if len(matrices) < 2:
            print(f"  [{stg}] Only {len(matrices)} run(s) with K={target_k}. Skipping.\n")
            continue

        run_names = sorted(matrices.keys())
        n_skills = len(matrices[run_names[0]][1])
        all_mats = [matrices[rn][2] for rn in run_names]

        # Validate dimensions
        if any(len(matrices[rn][1]) != n_skills for rn in run_names):
            print(f"  [{stg}] Inconsistent skill columns. Skipping.\n")
            continue

        # Permutation alignment (reuse from first stage when possible)
        if shared_perms is not None and all(rn in shared_perms for rn in run_names):
            aligned = [_apply_perm(m, shared_perms[rn])
                       for m, rn in zip(all_mats, run_names)]
        else:
            aligned, perm_list = _align_matrices(all_mats)
            shared_perms = dict(zip(run_names, perm_list))

        results[stg] = _analyze_stage(aligned, matrices[run_names[0]][0], run_names)

    # Print summary table
    if not results:
        print("No results to display.")
        return

    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    header_stages = [s for s in stages if s in results]
    print(f"  {'Metric':<25s}", end="")
    for s in header_stages:
        print(f"  {s:>12s}", end="")
    print()
    print(f"  {'-' * 25}", end="")
    for _ in header_stages:
        print(f"  {'-' * 12}", end="")
    print()

    rows = [
        ("Runs analyzed",      lambda m: f"{m['n_runs']}"),
        ("Element-wise agree", lambda m: f"{m['overall_agree'] * 100:.2f}%"),
        ("100% agree cells",   lambda m: f"{m['perfect_cells']}/{m['total_cells']}"),
        ("Item perfect agree", lambda m: f"{m['item_perfect_rate'] * 100:.1f}%"),
        ("Perfect Q-matrix",   lambda m: f"{m['perfect_qmatrix']}/{m['n_runs']}"),
        ("Avg Cohen's Kappa",  lambda m: f"{m['avg_kappa']:.4f}"),
        ("Min Cohen's Kappa",  lambda m: f"{m['min_kappa']:.4f}"),
    ]
    for name, fn in rows:
        print(f"  {name:<25s}", end="")
        for s in header_stages:
            print(f"  {fn(results[s]):>12s}", end="")
        print()

    print(f"\n  K consistency: {k_freq}/{len(k_values)} ({k_freq / len(k_values) * 100:.1f}%)")
    print()


if __name__ == "__main__":
    main()
