"""Create and summarize a reviewable canonical-skill mapping for B1 codebooks."""

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path


CANONICAL = {
    "C1": "Like-denominator fraction subtraction",
    "C2": "Unlike-denominator conversion and subtraction",
    "C3": "Whole-number minuend/operand handling",
    "C4": "Mixed-number subtraction without regrouping",
    "C5": "Borrowing/regrouping",
    "C6": "Improper mixed-number normalization",
    "C7": "Mixed-number/improper-fraction conversion",
    "C8": "Fraction simplification/reduction",
    "C9": "Generic fraction subtraction",
}


def draft_label(name, definition):
    name_text = name.lower()
    definition_text = definition.lower()
    text = f"{name_text} {definition_text}"
    if ("borrow" in name_text or "regroup" in name_text) and not any(
        x in name_text for x in ("without regroup", "no regroup")
    ):
        return "C5"
    if "mixed" in name_text and any(x in name_text for x in ("without regroup", "no regroup")):
        return "C4"
    if "whole-to-mixed" in name_text:
        return "C3"
    if any(x in name_text for x in ("mixed-improper", "convert mixed", "convert numbers", "convert to improper")):
        return "C7"
    if "improper" in name_text:
        return "C6"
    if "simplif" in name_text or "reduce" in name_text:
        return "C8"
    if "unlike" in name_text:
        return "C2"
    if "common denominator" in name_text or "common-denominator" in name_text:
        if "fraction subtraction" in name_text or "subtract" in name_text or "already" in definition_text:
            return "C1"
        return "C2"
    if any(x in name_text for x in ("basic fraction subtraction", "like denominator", "like-denominator", "same denominator", "numerator subtraction")):
        return "C1"
    if "fraction subtraction" in name_text and any(
        x in definition_text for x in ("same denominator", "common denominator", "subtract numerators")
    ):
        return "C1"
    if any(x in name_text for x in (
        "whole-number minuend", "whole number minuend", "whole-number operand",
        "whole number operand", "handling whole", "whole-fraction", "whole minus",
        "whole number minus",
    )):
        return "C3"
    if "mixed" in name_text:
        return "C4"
    if "whole number" in name_text or "whole-number" in name_text:
        return "C3"
    if any(x in definition_text for x in (
        "subtract numerators", "same denominator", "like denominator", "common denominator"
    )):
        return "C1"
    return "C9"


def create_draft(runs_root, run_glob, annotations_path):
    rows = []
    for run_dir in sorted(Path(runs_root).glob(run_glob)):
        config = json.loads((run_dir / "config.json").read_text())
        codebook = json.loads((run_dir / "codebook.json").read_text())
        for skill in codebook["skills"]:
            canonical_id = draft_label(skill["name"], skill["definition"])
            rows.append({
                "run_id": run_dir.name,
                "model": config["model"],
                "skill_id": skill["skill_id"],
                "original_name": skill["name"],
                "definition": skill["definition"],
                "canonical_id": canonical_id,
                "canonical_name": CANONICAL[canonical_id],
                "review_status": "draft_ai",
                "reviewer_note": "",
            })
    annotations_path.parent.mkdir(parents=True, exist_ok=True)
    with annotations_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(annotations_path):
    rows = list(csv.DictReader(annotations_path.open()))
    by_model_run = defaultdict(lambda: defaultdict(list))
    statuses = Counter()
    for row in rows:
        by_model_run[row["model"]][row["run_id"]].append(row["canonical_id"])
        statuses[row["review_status"]] += 1

    result = {
        "metric": "pairwise Jaccard similarity between canonical skill sets",
        "annotation_status": dict(statuses),
        "is_human_confirmed": bool(rows) and set(statuses) == {"human_confirmed"},
        "canonical_taxonomy": CANONICAL,
        "models": {},
    }
    for model, run_map in sorted(by_model_run.items()):
        sets = {run_id: set(labels) for run_id, labels in run_map.items()}
        pairwise = []
        for (run_a, set_a), (run_b, set_b) in combinations(sets.items(), 2):
            pairwise.append({
                "run_a": run_a,
                "run_b": run_b,
                "jaccard": round(len(set_a & set_b) / len(set_a | set_b), 4),
            })
        scores = [p["jaccard"] for p in pairwise]
        ontologies = Counter(tuple(sorted(s)) for s in sets.values())
        prevalence = Counter(label for labels in sets.values() for label in labels)
        duplicate_runs = sum(len(labels) != len(set(labels)) for labels in run_map.values())
        result["models"][model] = {
            "n_runs": len(run_map),
            "mean_pairwise_jaccard": round(statistics.mean(scores), 4),
            "sd_pairwise_jaccard": round(statistics.stdev(scores), 4),
            "min_pairwise_jaccard": round(min(scores), 4),
            "n_pairs": len(scores),
            "n_unique_canonical_ontologies": len(ontologies),
            "modal_ontology_frequency": max(ontologies.values()),
            "runs_with_mapping_collisions": duplicate_runs,
            "skill_prevalence": {
                label: {
                    "name": CANONICAL[label],
                    "runs": prevalence[label],
                    "fraction": round(prevalence[label] / len(run_map), 4),
                }
                for label in sorted(prevalence)
            },
            "pairwise": pairwise,
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", default="baseline_evaluation/runs")
    parser.add_argument("--run-glob", default="b1_naive_*_auto_run*")
    parser.add_argument("--annotations", default="baseline_evaluation/b1_analysis/codebook_annotations_draft.csv")
    parser.add_argument("--out", default="baseline_evaluation/b1_analysis/codebook_stability.json")
    parser.add_argument("--create-draft", action="store_true")
    parser.add_argument("--force-draft", action="store_true")
    args = parser.parse_args()

    annotations_path = Path(args.annotations)
    if args.create_draft:
        if annotations_path.exists() and not args.force_draft:
            parser.error(f"{annotations_path} already exists; use --force-draft to replace it")
        create_draft(args.runs_root, args.run_glob, annotations_path)
    result = summarize(annotations_path)
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
