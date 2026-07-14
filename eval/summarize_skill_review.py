"""Summarize reviewed per-run canonical skill sets without embeddings."""

import argparse
import json
from collections import Counter
from pathlib import Path


def summarize(review):
    result = {
        "review_status": review["review_status"],
        "counting_rule": review["counting_rule"],
        "taxonomy": review["taxonomy"],
        "models": {},
    }
    for model, runs in review["models"].items():
        sets = [tuple(sorted(run["skills"])) for run in runs]
        set_counts = Counter(sets)
        prevalence = Counter(skill for skill_set in sets for skill in skill_set)
        result["models"][model] = {
            "n_runs": len(runs),
            "raw_skill_instances": sum(run["raw_k"] for run in runs),
            "n_unique_canonical_skills": len(prevalence),
            "core_skills_10_of_10": sorted(
                skill for skill, count in prevalence.items() if count == len(runs)
            ),
            "n_core_skills_10_of_10": sum(count == len(runs) for count in prevalence.values()),
            "modal_skill_set": list(set_counts.most_common(1)[0][0]),
            "modal_skill_set_frequency": set_counts.most_common(1)[0][1],
            "modal_skill_set_rate": round(set_counts.most_common(1)[0][1] / len(runs), 4),
            "n_distinct_skill_sets": len(set_counts),
            "skill_prevalence": {
                skill: {
                    "name": review["taxonomy"][skill],
                    "runs": prevalence[skill],
                    "rate": round(prevalence[skill] / len(runs), 4),
                }
                for skill in sorted(prevalence)
            },
            "runs": runs,
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    review = json.loads(Path(args.review).read_text())
    result = summarize(review)
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
