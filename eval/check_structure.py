"""Structural validity checks for a Q-matrix (data-free, dimension A of the framework).

Errors: all-zero rows, all-zero columns, duplicate columns, under-covered skills.
Warning: skills with no single-attribute item (identifiability heuristic).
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_stability import load_qmatrix  # noqa: E402


def check_structure(items, skills, matrix, min_items_per_skill=2):
    n_items = len(matrix)
    n_skills = len(matrix[0]) if matrix else 0
    checks = {}
    violations = []

    zero_rows = [items[i] for i in range(n_items) if sum(matrix[i]) == 0]
    checks["all_zero_rows"] = {"passed": not zero_rows, "details": zero_rows}
    for item in zero_rows:
        violations.append({"level": "error", "rule": "all_zero_row",
                           "detail": f"item {item} measures no skill"})

    col_sums = [sum(matrix[i][j] for i in range(n_items)) for j in range(n_skills)]
    zero_cols = [skills[j] for j in range(n_skills) if col_sums[j] == 0]
    checks["all_zero_cols"] = {"passed": not zero_cols, "details": zero_cols}
    for skill in zero_cols:
        violations.append({"level": "error", "rule": "all_zero_col",
                           "detail": f"skill {skill} is measured by no item"})

    dup_pairs = []
    for a in range(n_skills):
        for b in range(a + 1, n_skills):
            if all(matrix[i][a] == matrix[i][b] for i in range(n_items)):
                dup_pairs.append([skills[a], skills[b]])
    checks["duplicate_cols"] = {"passed": not dup_pairs, "details": dup_pairs}
    for pair in dup_pairs:
        violations.append({"level": "error", "rule": "duplicate_cols",
                           "detail": f"skills {pair[0]} and {pair[1]} have identical columns"})

    under_covered = [
        {"skill": skills[j], "n_items": col_sums[j]}
        for j in range(n_skills) if 0 < col_sums[j] < min_items_per_skill
    ]
    checks["skill_coverage"] = {"passed": not under_covered, "details": under_covered,
                                "min_items_per_skill": min_items_per_skill}
    for uc in under_covered:
        violations.append({"level": "error", "rule": "skill_coverage",
                           "detail": f"skill {uc['skill']} measured by only {uc['n_items']} item(s)"})

    single_attr_counts = {}
    for j in range(n_skills):
        single_attr_counts[skills[j]] = sum(
            1 for i in range(n_items) if matrix[i][j] == 1 and sum(matrix[i]) == 1
        )
    no_single = [s for s, c in single_attr_counts.items() if c == 0]
    checks["single_attribute_item"] = {"passed": not no_single,
                                       "details": {"counts": single_attr_counts,
                                                   "skills_without": no_single}}
    for skill in no_single:
        violations.append({"level": "warning", "rule": "single_attribute_item",
                           "detail": f"skill {skill} has no single-attribute item (identifiability heuristic)"})

    row_sums = Counter(sum(row) for row in matrix)
    total_ones = sum(col_sums)

    return {
        "n_items": n_items,
        "n_skills": n_skills,
        "checks": checks,
        "violations": violations,
        "n_errors": sum(1 for v in violations if v["level"] == "error"),
        "n_warnings": sum(1 for v in violations if v["level"] == "warning"),
        "item_skill_count_distribution": {str(k): row_sums[k] for k in sorted(row_sums)},
        "density": round(total_ones / (n_items * n_skills), 4) if n_items and n_skills else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Structural validity checks for a Q-matrix CSV.")
    parser.add_argument("qmatrix", help="Path to Q.csv")
    parser.add_argument("--min_items_per_skill", type=int, default=2)
    parser.add_argument("--output", default=None, help="Output JSON path (default: stdout)")
    args = parser.parse_args()

    items, skills, matrix = load_qmatrix(args.qmatrix)
    result = check_structure(items, skills, matrix, args.min_items_per_skill)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Structure report written to: {args.output}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
