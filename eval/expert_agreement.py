"""Aligned agreement between a method Q-matrix and the expert Q (dimension D).

Equal K: exact column-permutation alignment (max cell agreement).
Unequal K: best injective assignment of the smaller side's columns into the
larger side's columns (brute force over ordered subsets; P(8,4)=1680).
"""
import argparse
import json
import sys
from itertools import permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_stability import load_qmatrix  # noqa: E402


def _column(matrix, j):
    return [row[j] for row in matrix]


def _agreement_for_assignment(q_method, q_expert, assignment):
    """Cell agreement + 1-cell precision/recall over matched column pairs.

    assignment: list of (method_col, expert_col) pairs.
    """
    n_items = len(q_method)
    matches = tp = fp = fn = 0
    for mj, ej in assignment:
        for i in range(n_items):
            m, e = q_method[i][mj], q_expert[i][ej]
            matches += (m == e)
            tp += (m == 1 and e == 1)
            fp += (m == 1 and e == 0)
            fn += (m == 0 and e == 1)
    total = n_items * len(assignment)
    return {
        "cell_agreement": matches / total if total else 0.0,
        "precision_1cells": tp / (tp + fp) if (tp + fp) else None,
        "recall_1cells": tp / (tp + fn) if (tp + fn) else None,
    }


def aligned_agreement(q_method, q_expert, method_skills=None, expert_skills=None):
    """Find the column assignment maximizing cell agreement; report metrics."""
    k_m = len(q_method[0])
    k_e = len(q_expert[0])

    if k_m <= k_e:
        candidate_assignments = (
            list(zip(range(k_m), perm)) for perm in permutations(range(k_e), k_m)
        )
    else:
        candidate_assignments = (
            list(zip(perm, range(k_e))) for perm in permutations(range(k_m), k_e)
        )

    best, best_assignment = None, None
    for assignment in candidate_assignments:
        metrics = _agreement_for_assignment(q_method, q_expert, assignment)
        if best is None or metrics["cell_agreement"] > best["cell_agreement"]:
            best, best_assignment = metrics, assignment

    matched_expert = {ej for _mj, ej in best_assignment}
    matched_method = {mj for mj, _ej in best_assignment}
    result = {
        "k_method": k_m,
        "k_expert": k_e,
        "n_matched_skills": len(best_assignment),
        "n_unmatched_expert_skills": k_e - len(matched_expert),
        "n_unmatched_method_skills": k_m - len(matched_method),
        "cell_agreement": round(best["cell_agreement"], 4),
        "precision_1cells": round(best["precision_1cells"], 4) if best["precision_1cells"] is not None else None,
        "recall_1cells": round(best["recall_1cells"], 4) if best["recall_1cells"] is not None else None,
        "assignment": [list(pair) for pair in best_assignment],
    }
    if method_skills and expert_skills:
        result["matched_pairs"] = [
            [method_skills[mj], expert_skills[ej]] for mj, ej in best_assignment
        ]
    return result


def main():
    parser = argparse.ArgumentParser(description="Aligned agreement between method Q and expert Q.")
    parser.add_argument("--qmatrix", required=True, help="Method Q.csv")
    parser.add_argument("--expert_q", default="data/expert_q_tatsuoka.csv")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    _items_m, skills_m, q_method = load_qmatrix(args.qmatrix)
    _items_e, skills_e, q_expert = load_qmatrix(args.expert_q)
    result = aligned_agreement(q_method, q_expert, skills_m, skills_e)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Expert agreement written to: {args.output}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
