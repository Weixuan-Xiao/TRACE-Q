"""analyze_stability.py — Cross-run stability analysis for the Q-matrix pipeline.

Usage
-----
    python analyze_stability.py [BASE_DIR] [TARGET_K]

Examples
--------
    python analyze_stability.py outputs_exp/v2        # auto-detect K
    python analyze_stability.py outputs_exp/v2 5      # force K=5
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path


# ---------------------------------------------------------------------------
# Minimal numpy-free matrix helpers (so no extra dependency is required)
# ---------------------------------------------------------------------------

def _zeros(rows: int, cols: int) -> list[list[float]]:
    return [[0.0] * cols for _ in range(rows)]


def _load_qmatrix(csv_path: Path) -> tuple[list[str], list[str], list[list[int]]]:
    """Load a Q-matrix CSV → (item_ids, skill_ids, matrix[row][col])."""
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        # Detect optional trailing columns like "audit_verdict"
        skill_cols = [h for h in header[1:] if h.startswith("S")]
        n_skills = len(skill_cols)
        items: list[str] = []
        rows: list[list[int]] = []
        for row in reader:
            items.append(row[0])
            rows.append([int(row[1 + c]) for c in range(n_skills)])
    return items, skill_cols, rows


def _load_codebook(json_path: Path) -> list[dict]:
    with open(json_path) as f:
        data = json.load(f)
    return data.get("codebook") or data.get("final_codebook", [])


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def _fleiss_kappa(matrix_stack: list[list[list[int]]]) -> float:
    """Fleiss' kappa treating each run as a rater & each Q-matrix cell as a subject.

    matrix_stack: list of Q-matrices (one per run), each matrix is [items][skills].
    """
    n_runs = len(matrix_stack)
    n_items = len(matrix_stack[0])
    n_skills = len(matrix_stack[0][0])
    N = n_items * n_skills  # total subjects

    count_1 = [0] * N
    for mat in matrix_stack:
        idx = 0
        for i in range(n_items):
            for j in range(n_skills):
                count_1[idx] += mat[i][j]
                idx += 1

    # P_i per subject
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


def _cohens_kappa(v1: list[int], v2: list[int]) -> float:
    n = len(v1)
    agree = sum(a == b for a, b in zip(v1, v2))
    po = agree / n
    mean1 = sum(v1) / n
    mean2 = sum(v2) / n
    pe = mean1 * mean2 + (1 - mean1) * (1 - mean2)
    if pe >= 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def _interpret_kappa(k: float) -> str:
    if k > 0.80:
        return "Almost perfect agreement ✓"
    if k > 0.60:
        return "Substantial agreement"
    if k > 0.40:
        return "Moderate agreement"
    if k > 0.20:
        return "Fair agreement ⚠"
    return "Poor agreement ✗"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("outputs_exp/v2")
    target_k: int | None = int(sys.argv[2]) if len(sys.argv) > 2 else None

    # Discover runs
    run_dirs = sorted(
        [d for d in base.iterdir() if d.is_dir() and d.name.startswith("run")],
        key=lambda p: int(p.name.removeprefix("run")),
    )
    print(f"Found {len(run_dirs)} runs: {[d.name for d in run_dirs]}\n")
    if len(run_dirs) < 2:
        print("Need at least 2 runs for stability analysis.")
        return

    # ── 1. K Consistency ──────────────────────────────────────────
    print("=" * 60)
    print("1. K Consistency (K_max per run)")
    print("=" * 60)
    k_values: dict[str, int] = {}
    for rd in run_dirs:
        cb_path = rd / "step3_skill_codebook.json"
        if cb_path.exists():
            cb = _load_codebook(cb_path)
            k_values[rd.name] = len(cb)
            print(f"  {rd.name}: K_max = {len(cb)}")
    if not k_values:
        print("  No codebooks found. Aborting.")
        return
    counts = Counter(k_values.values())
    most_common_k, freq = counts.most_common(1)[0]
    print(f"\n  Most common K = {most_common_k} ({freq}/{len(k_values)} runs)")
    print(f"  K consistency  = {freq / len(k_values) * 100:.1f}%\n")

    if target_k is None:
        target_k = most_common_k
    print(f"→ Analyzing Q-matrices at K = {target_k}\n")

    # ── 2. Load Q-matrices ────────────────────────────────────────
    matrices: dict[str, tuple[list[str], list[str], list[list[int]]]] = {}
    for rd in run_dirs:
        # Prefer exported Q-matrix; fall back to audited version
        qm_path = rd / f"step6_Q_matrix_K{target_k}.csv"
        if not qm_path.exists():
            qm_path = rd / f"step8_auditor_Q_matrix_K{target_k}_reviewed.csv"
        if qm_path.exists():
            matrices[rd.name] = _load_qmatrix(qm_path)

    if len(matrices) < 2:
        print(f"Only {len(matrices)} run(s) have a K={target_k} Q-matrix. Need ≥ 2.")
        return
    print(f"Loaded {len(matrices)} Q-matrices for K={target_k}\n")

    run_names = sorted(matrices.keys())
    ref_items = matrices[run_names[0]][0]
    n_items = len(ref_items)
    n_skills = target_k
    n_runs = len(run_names)

    all_mats = [matrices[rn][2] for rn in run_names]

    # ── 3. Element-wise Agreement ─────────────────────────────────
    print("=" * 60)
    print("2. Element-wise Agreement Rate")
    print("=" * 60)
    # Majority vote per cell
    majority = _zeros(n_items, n_skills)
    for mat in all_mats:
        for i in range(n_items):
            for j in range(n_skills):
                majority[i][j] += mat[i][j]
    majority_bin = [[1 if majority[i][j] / n_runs >= 0.5 else 0 for j in range(n_skills)] for i in range(n_items)]

    agree_counts = _zeros(n_items, n_skills)
    for mat in all_mats:
        for i in range(n_items):
            for j in range(n_skills):
                if mat[i][j] == majority_bin[i][j]:
                    agree_counts[i][j] += 1

    cell_agree = [[agree_counts[i][j] / n_runs for j in range(n_skills)] for i in range(n_items)]
    flat_agree = [cell_agree[i][j] for i in range(n_items) for j in range(n_skills)]
    overall = sum(flat_agree) / len(flat_agree)
    perfect_cells = sum(1 for v in flat_agree if v == 1.0)
    min_cell = min(flat_agree)

    print(f"  Overall element-wise agreement: {overall * 100:.2f}%")
    print(f"  Min cell agreement:             {min_cell * 100:.1f}%")
    print(f"  Cells with 100% agreement:      {perfect_cells}/{n_items * n_skills}")
    print()

    # ── 4. Item-level Perfect Agreement ───────────────────────────
    print("=" * 60)
    print("3. Item-level Perfect Agreement")
    print("=" * 60)
    item_perfect_count = 0
    for i in range(n_items):
        vectors = set()
        for mat in all_mats:
            vectors.add(tuple(mat[i]))
        if len(vectors) == 1:
            item_perfect_count += 1
        else:
            vec_counter = Counter(tuple(mat[i]) for mat in all_mats)
            print(f"  {ref_items[i]}: {len(vectors)} distinct vectors — {dict(vec_counter)}")

    perfect_rate = item_perfect_count / n_items
    print(f"\n  Items with perfect agreement: {item_perfect_count}/{n_items} ({perfect_rate * 100:.1f}%)\n")

    # ── 5. Pairwise Cohen's Kappa & Hamming ───────────────────────
    print("=" * 60)
    print("4. Pairwise Run Comparisons (Cohen's Kappa & Hamming)")
    print("=" * 60)
    hamming_list: list[int] = []
    kappa_list: list[float] = []
    for (idx1, name1), (idx2, name2) in combinations(enumerate(run_names), 2):
        flat1 = [all_mats[idx1][i][j] for i in range(n_items) for j in range(n_skills)]
        flat2 = [all_mats[idx2][i][j] for i in range(n_items) for j in range(n_skills)]
        hamming = sum(a != b for a, b in zip(flat1, flat2))
        kappa = _cohens_kappa(flat1, flat2)
        hamming_list.append(hamming)
        kappa_list.append(kappa)

    avg_hamming = sum(hamming_list) / len(hamming_list)
    avg_kappa = sum(kappa_list) / len(kappa_list)
    min_kappa = min(kappa_list)

    print(f"  Avg pairwise Hamming distance: {avg_hamming:.2f} / {n_items * n_skills} cells")
    print(f"  Avg pairwise Cohen's Kappa:    {avg_kappa:.4f}")
    print(f"  Min pairwise Cohen's Kappa:    {min_kappa:.4f}")
    print()

    # ── 6. Fleiss' Kappa ──────────────────────────────────────────
    print("=" * 60)
    print("5. Fleiss' Kappa (multi-run agreement)")
    print("=" * 60)
    fk = _fleiss_kappa(all_mats)
    print(f"  Fleiss' Kappa: {fk:.4f}")
    print(f"  Interpretation: {_interpret_kappa(fk)}")

    # ── Summary ───────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Runs analyzed:           {n_runs}")
    print(f"  K level:                 {target_k}")
    print(f"  K consistency:           {freq}/{len(k_values)} ({freq / len(k_values) * 100:.1f}%)")
    print(f"  Element-wise agreement:  {overall * 100:.2f}%")
    print(f"  Item perfect agreement:  {perfect_rate * 100:.1f}%")
    print(f"  Avg Cohen's Kappa:       {avg_kappa:.4f}")
    print(f"  Fleiss' Kappa:           {fk:.4f}")
    print()


if __name__ == "__main__":
    main()
