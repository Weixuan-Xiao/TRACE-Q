"""analyze_stability.py — Cross-run stability analysis for the Q-matrix pipeline.

Compares pre-audit (step6) and post-audit (step8) Q-matrices to quantify
both pipeline stability and Auditor impact.

Usage
-----
    python analyze_stability.py [BASE_DIR] [TARGET_K] [--stage {step6,step8,both}]

Examples
--------
    python analyze_stability.py outputs_exp/v2              # auto K, both stages
    python analyze_stability.py outputs_exp/v2 5            # force K=5, both stages
    python analyze_stability.py outputs_exp/v2 5 --stage step6   # only pre-audit
    python analyze_stability.py outputs_exp/v2 5 --stage both    # compare both
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_META_COLS = {"item_id", "audit_verdict", "audit_note"}


def _zeros(rows: int, cols: int) -> list[list[float]]:
    return [[0.0] * cols for _ in range(rows)]


def _load_qmatrix(csv_path: Path) -> tuple[list[str], list[str], list[list[int]]]:
    """Load a Q-matrix CSV → (item_ids, skill_ids, matrix[row][col]).

    Skill columns are all columns after ``item_id`` that are not known metadata
    (e.g. ``audit_verdict``).  Works with any skill-ID prefix (S01, M01 …).
    """
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        skill_cols = [h for h in header[1:] if h not in _META_COLS]
        col_indices = [header.index(h) for h in skill_cols]
        items: list[str] = []
        rows: list[list[int]] = []
        for row in reader:
            items.append(row[0])
            # Strip trailing '*' from auditor-marked cells (e.g. "0*" → 0)
            rows.append([int(row[c].rstrip("*")) for c in col_indices])
    return items, skill_cols, rows


def _load_codebook(json_path: Path) -> list[dict]:
    with open(json_path) as f:
        data = json.load(f)
    return data.get("skills") or data.get("codebook") or data.get("final_codebook", [])


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def _fleiss_kappa(matrix_stack: list[list[list[int]]]) -> float:
    """Fleiss' kappa — each run is a rater, each Q-matrix cell is a subject."""
    n_runs = len(matrix_stack)
    n_items = len(matrix_stack[0])
    n_skills = len(matrix_stack[0][0])
    N = n_items * n_skills

    count_1 = [0] * N
    for mat in matrix_stack:
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
# Core analysis — returns a metrics dict for one stage
# ---------------------------------------------------------------------------

def _analyze_stage(
    all_mats: list[list[list[int]]],
    ref_items: list[str],
    run_names: list[str],
    label: str,
) -> dict:
    """Run the full suite of stability metrics and print results.

    Returns a dict of key metrics for later comparison.
    """
    n_runs = len(all_mats)
    n_items = len(ref_items)
    n_skills = len(all_mats[0][0])

    print("=" * 60)
    print(f"  STAGE: {label}")
    print("=" * 60)

    # ── Element-wise Agreement ────────────────────────────────────
    majority = _zeros(n_items, n_skills)
    for mat in all_mats:
        for i in range(n_items):
            for j in range(n_skills):
                majority[i][j] += mat[i][j]
    majority_bin = [
        [1 if majority[i][j] / n_runs >= 0.5 else 0 for j in range(n_skills)]
        for i in range(n_items)
    ]

    agree_counts = _zeros(n_items, n_skills)
    for mat in all_mats:
        for i in range(n_items):
            for j in range(n_skills):
                if mat[i][j] == majority_bin[i][j]:
                    agree_counts[i][j] += 1

    cell_agree = [
        [agree_counts[i][j] / n_runs for j in range(n_skills)]
        for i in range(n_items)
    ]
    flat_agree = [cell_agree[i][j] for i in range(n_items) for j in range(n_skills)]
    overall_agree = sum(flat_agree) / len(flat_agree)
    perfect_cells = sum(1 for v in flat_agree if v == 1.0)
    min_cell = min(flat_agree)

    print(f"\n  1. Element-wise Agreement Rate")
    print(f"     Overall:           {overall_agree * 100:.2f}%")
    print(f"     Min cell:          {min_cell * 100:.1f}%")
    print(f"     100% agree cells:  {perfect_cells}/{n_items * n_skills}")

    # ── Item-level Perfect Agreement ──────────────────────────────
    item_perfect_count = 0
    disagreed_items: list[str] = []
    for i in range(n_items):
        vectors = set(tuple(mat[i]) for mat in all_mats)
        if len(vectors) == 1:
            item_perfect_count += 1
        else:
            vec_counter = Counter(tuple(mat[i]) for mat in all_mats)
            disagreed_items.append(ref_items[i])
            print(f"     ≠ {ref_items[i]}: {len(vectors)} variants — {dict(vec_counter)}")

    perfect_rate = item_perfect_count / n_items
    print(f"\n  2. Item-level Perfect Agreement")
    print(f"     Perfect items: {item_perfect_count}/{n_items} ({perfect_rate * 100:.1f}%)")

    # ── Pairwise Cohen's Kappa & Hamming ──────────────────────────
    hamming_list: list[int] = []
    kappa_list: list[float] = []
    for (idx1, _), (idx2, _) in combinations(enumerate(run_names), 2):
        flat1 = [all_mats[idx1][i][j] for i in range(n_items) for j in range(n_skills)]
        flat2 = [all_mats[idx2][i][j] for i in range(n_items) for j in range(n_skills)]
        hamming_list.append(sum(a != b for a, b in zip(flat1, flat2)))
        kappa_list.append(_cohens_kappa(flat1, flat2))

    avg_hamming = sum(hamming_list) / len(hamming_list)
    avg_kappa = sum(kappa_list) / len(kappa_list)
    min_kappa = min(kappa_list)

    print(f"\n  3. Pairwise Comparisons")
    print(f"     Avg Hamming distance: {avg_hamming:.2f} / {n_items * n_skills} cells")
    print(f"     Avg Cohen's Kappa:    {avg_kappa:.4f}")
    print(f"     Min Cohen's Kappa:    {min_kappa:.4f}")

    # ── Fleiss' Kappa ─────────────────────────────────────────────
    fk = _fleiss_kappa(all_mats)
    print(f"\n  4. Fleiss' Kappa:        {fk:.4f}  ({_interpret_kappa(fk)})")
    print()

    return {
        "label": label,
        "overall_agree": overall_agree,
        "perfect_rate": perfect_rate,
        "avg_hamming": avg_hamming,
        "avg_kappa": avg_kappa,
        "min_kappa": min_kappa,
        "fleiss_kappa": fk,
        "perfect_cells": perfect_cells,
        "total_cells": n_items * n_skills,
        "disagreed_items": disagreed_items,
        "all_mats": all_mats,
    }


# ---------------------------------------------------------------------------
# Load Q-matrices for a given stage pattern
# ---------------------------------------------------------------------------

def _load_stage_matrices(
    run_dirs: list[Path],
    target_k: int,
    stage: str,
) -> dict[str, tuple[list[str], list[str], list[list[int]]]]:
    """Load Q-matrices from all runs for the given stage and K."""
    matrices: dict[str, tuple[list[str], list[str], list[list[int]]]] = {}
    for rd in run_dirs:
        if stage == "step6":
            qm_path = rd / f"step6_Q_matrix_K{target_k}.csv"
        else:  # step8
            qm_path = rd / f"step8_auditor_Q_matrix_K{target_k}_reviewed.csv"
        if qm_path.exists():
            matrices[rd.name] = _load_qmatrix(qm_path)
    return matrices


# ---------------------------------------------------------------------------
# Auditor impact comparison
# ---------------------------------------------------------------------------

def _compare_stages(
    metrics6: dict,
    metrics8: dict,
    run_names: list[str],
    ref_items: list[str],
    n_skills: int,
) -> None:
    """Print a detailed Auditor Impact comparison."""
    n_items = len(ref_items)
    n_runs = len(run_names)

    print("=" * 60)
    print("  AUDITOR IMPACT (step6 → step8)")
    print("=" * 60)

    # Delta metrics
    def _delta(name: str, key: str, fmt: str = ".2f", pct: bool = False) -> None:
        v6 = metrics6[key]
        v8 = metrics8[key]
        d = v8 - v6
        if pct:
            s6, s8, sd = f"{v6 * 100:{fmt}}%", f"{v8 * 100:{fmt}}%", f"{d * 100:+{fmt}}%"
        else:
            s6, s8, sd = f"{v6:{fmt}}", f"{v8:{fmt}}", f"{d:+{fmt}}"
        arrow = "✓" if d > 0 else ("⚠" if d < 0 else "—")
        if key == "avg_hamming":  # lower is better for Hamming
            arrow = "✓" if d < 0 else ("⚠" if d > 0 else "—")
        print(f"  {name:30s}  {s6:>10s} → {s8:>10s}  (Δ = {sd}) {arrow}")

    _delta("Element-wise agreement", "overall_agree", ".2f", pct=True)
    _delta("Item perfect agreement", "perfect_rate", ".1f", pct=True)
    _delta("Avg Hamming distance", "avg_hamming", ".2f")
    _delta("Avg Cohen's Kappa", "avg_kappa", ".4f")
    _delta("Min Cohen's Kappa", "min_kappa", ".4f")
    _delta("Fleiss' Kappa", "fleiss_kappa", ".4f")
    print()

    # Per-run cell flip counts
    mats6 = metrics6["all_mats"]
    mats8 = metrics8["all_mats"]
    total_flips = 0
    flip_01 = 0  # 0→1
    flip_10 = 0  # 1→0
    for r in range(n_runs):
        for i in range(n_items):
            for j in range(n_skills):
                v6 = mats6[r][i][j]
                v8 = mats8[r][i][j]
                if v6 != v8:
                    total_flips += 1
                    if v6 == 0:
                        flip_01 += 1
                    else:
                        flip_10 += 1

    avg_flips = total_flips / n_runs if n_runs else 0
    print(f"  Cells flipped by Auditor")
    print(f"    Total across all runs:   {total_flips}")
    print(f"    Avg per run:             {avg_flips:.1f} / {n_items * n_skills} cells")
    print(f"    0→1 (skill added):       {flip_01}")
    print(f"    1→0 (skill removed):     {flip_10}")
    print()

    # Verdict
    d_fleiss = metrics8["fleiss_kappa"] - metrics6["fleiss_kappa"]
    d_agree = metrics8["overall_agree"] - metrics6["overall_agree"]
    if total_flips == 0:
        verdict = "Auditor made NO changes — step6 and step8 are identical."
    elif d_fleiss > 0.005 and d_agree > 0.005:
        verdict = "Auditor IMPROVED cross-run stability ✓"
    elif d_fleiss < -0.005 or d_agree < -0.005:
        verdict = "Auditor DECREASED cross-run stability ⚠  (may be introducing run-specific noise)"
    else:
        verdict = "Auditor had NEGLIGIBLE impact on cross-run stability —"

    print(f"  Verdict: {verdict}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-run stability analysis for Q-matrix pipeline.")
    parser.add_argument("base_dir", nargs="?", default="outputs_exp/v2", help="Base directory containing run* folders.")
    parser.add_argument("target_k", nargs="?", type=int, default=None, help="K level to analyze (auto-detected if omitted).")
    parser.add_argument(
        "--stage",
        choices=["step6", "step8", "both"],
        default="both",
        help="Which Q-matrix stage to analyze: step6 (pre-audit), step8 (post-audit), or both (default).",
    )
    args = parser.parse_args()

    base = Path(args.base_dir)
    target_k: int | None = args.target_k
    stage = args.stage

    # Discover runs
    run_dirs = sorted(
        [d for d in base.iterdir() if d.is_dir() and d.name.startswith("run")],
        key=lambda p: int(p.name.removeprefix("run")),
    )
    print(f"Found {len(run_dirs)} runs: {[d.name for d in run_dirs]}\n")
    if len(run_dirs) < 2:
        print("Need at least 2 runs for stability analysis.")
        return

    # ── K Consistency ─────────────────────────────────────────────
    print("=" * 60)
    print("  K CONSISTENCY (K_max per run)")
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

    # ── Run analysis per stage ────────────────────────────────────
    stages_to_run = ["step6", "step8"] if stage == "both" else [stage]
    results: dict[str, dict] = {}

    for stg in stages_to_run:
        label = f"{stg} ({'Pre-Audit' if stg == 'step6' else 'Post-Audit'})"
        matrices = _load_stage_matrices(run_dirs, target_k, stg)
        if len(matrices) < 2:
            print(f"  [{stg}] Only {len(matrices)} run(s) have K={target_k} Q-matrix. Skipping.\n")
            continue

        run_names = sorted(matrices.keys())
        ref_items = matrices[run_names[0]][0]
        n_skills_actual = len(matrices[run_names[0]][1])
        all_mats = [matrices[rn][2] for rn in run_names]

        # Validate dimensions
        valid = True
        for rn in run_names:
            cols = len(matrices[rn][1])
            if cols != n_skills_actual:
                print(f"  ⚠ {rn}: {cols} skill columns (expected {n_skills_actual}). Skipping stage.")
                valid = False
                break
        if not valid:
            continue

        print(f"  Loaded {len(matrices)} Q-matrices ({n_skills_actual} skills) for {stg}\n")
        m = _analyze_stage(all_mats, ref_items, run_names, label)
        m["n_skills"] = n_skills_actual
        m["run_names"] = run_names
        m["ref_items"] = ref_items
        results[stg] = m

    # ── Auditor Impact comparison ─────────────────────────────────
    if "step6" in results and "step8" in results:
        m6 = results["step6"]
        m8 = results["step8"]
        # Ensure same runs are compared
        common_runs = sorted(set(m6["run_names"]) & set(m8["run_names"]))
        if len(common_runs) >= 2:
            _compare_stages(m6, m8, common_runs, m6["ref_items"], m6["n_skills"])

    # ── Summary table ─────────────────────────────────────────────
    if results:
        print("=" * 60)
        print("  SUMMARY")
        print("=" * 60)
        print(f"  {'Metric':<30s}", end="")
        for stg in stages_to_run:
            if stg in results:
                print(f"  {stg:>12s}", end="")
        print()
        print(f"  {'-' * 30}", end="")
        for stg in stages_to_run:
            if stg in results:
                print(f"  {'-' * 12}", end="")
        print()

        rows = [
            ("Runs analyzed",          lambda m: f"{len(m['run_names'])}"),
            ("Element-wise agree",     lambda m: f"{m['overall_agree'] * 100:.2f}%"),
            ("100% agree cells",       lambda m: f"{m['perfect_cells']}/{m['total_cells']}"),
            ("Item perfect agree",     lambda m: f"{m['perfect_rate'] * 100:.1f}%"),
            ("Avg Hamming dist",       lambda m: f"{m['avg_hamming']:.2f}"),
            ("Avg Cohen's Kappa",      lambda m: f"{m['avg_kappa']:.4f}"),
            ("Min Cohen's Kappa",      lambda m: f"{m['min_kappa']:.4f}"),
            ("Fleiss' Kappa",          lambda m: f"{m['fleiss_kappa']:.4f}"),
        ]
        for name, fn in rows:
            print(f"  {name:<30s}", end="")
            for stg in stages_to_run:
                if stg in results:
                    print(f"  {fn(results[stg]):>12s}", end="")
            print()

        # K consistency (stage-independent)
        print(f"\n  K consistency: {freq}/{len(k_values)} ({freq / len(k_values) * 100:.1f}%)")
        print()


if __name__ == "__main__":
    main()
