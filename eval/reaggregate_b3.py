"""Rebuild B3 final artifacts from saved constituent samples."""

import argparse
import datetime
import json
from collections import Counter, defaultdict
from pathlib import Path

from evaluate_stability import load_qmatrix
from eval.baselines import aggregate_b3, load_items
from eval.contract import validate_run
from eval.convert_legacy import _write_canonical_q
from eval.report import evaluate_one_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", default="baseline_evaluation/runs")
    parser.add_argument("--run-glob", default="b3_sc5_*_auto_run*")
    parser.add_argument("--items", default="data/items.jsonl")
    parser.add_argument("--per-run-cache", default="baseline_evaluation/report/per_run")
    parser.add_argument("--expert-q", default="data/expert_q_tatsuoka.csv")
    parser.add_argument(
        "--audit-out", default="baseline_evaluation/b3_analysis/b3_aggregation_audit.json"
    )
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()

    item_ids = [item["item_id"] for item in load_items(args.items)]
    run_dirs = sorted(Path(args.runs_root).glob(args.run_glob))
    if not run_dirs:
        raise RuntimeError(f"no B3 runs matched {args.run_glob!r}")

    rebuilt = []
    model_audit = defaultdict(lambda: {
        "runs": 0,
        "samples_expected": 0,
        "samples_successful": 0,
        "input_k_distribution": Counter(),
        "valid_k_distribution": Counter(),
        "final_k_distribution": Counter(),
        "samples_valid": 0,
        "samples_excluded_structure": 0,
        "samples_retained": 0,
        "runs_with_tied_modal_k": [],
        "runs_with_even_retained_samples": [],
        "cell_vote_ties_by_run": {},
        "successful_api_calls": 0,
        "temperature_fallbacks": 0,
    })
    structural_exclusions = []
    order_independence_checked = 0
    qmatrix_mismatches = 0
    codebook_mismatches = 0
    for run_dir in run_dirs:
        sample_records = json.loads((run_dir / "b3_samples.json").read_text())
        samples = [
            (record["skills"], record["matrix"])
            for record in sample_records if "skills" in record and "matrix" in record
        ]
        skills, matrix, meta = aggregate_b3(samples)
        reversed_skills, reversed_matrix, _reversed_meta = aggregate_b3(
            list(reversed(samples))
        )
        if reversed_skills != skills or reversed_matrix != matrix:
            raise RuntimeError(f"aggregation depends on sample order: {run_dir}")
        order_independence_checked += 1
        skill_ids = [skill["skill_id"] for skill in skills]

        _write_canonical_q(item_ids, skill_ids, matrix, run_dir / "Q.csv")
        (run_dir / "codebook.json").write_text(
            json.dumps({"skills": skills}, indent=2) + "\n"
        )

        _written_items, written_skill_ids, written_matrix = load_qmatrix(
            run_dir / "Q.csv"
        )
        if written_skill_ids != skill_ids or written_matrix != matrix:
            qmatrix_mismatches += 1
        written_codebook = json.loads((run_dir / "codebook.json").read_text())
        if written_codebook != {"skills": skills}:
            codebook_mismatches += 1

        config_path = run_dir / "config.json"
        config = json.loads(config_path.read_text())
        config["k_selected"] = len(skills)
        config["method_version"] = "phase2-v2"
        config["aggregation_recomputed_at"] = datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat()
        config["b3"] = meta
        config_path.write_text(json.dumps(config, indent=2) + "\n")

        model = config["model"]
        audit = model_audit[model]
        audit["runs"] += 1
        audit["samples_expected"] += len(sample_records)
        audit["samples_successful"] += len(samples)
        audit["input_k_distribution"].update(
            {int(k): count for k, count in meta["input_k_distribution"].items()}
        )
        audit["valid_k_distribution"].update(
            {int(k): count for k, count in meta["k_distribution"].items()}
        )
        audit["final_k_distribution"][len(skills)] += 1
        audit["samples_valid"] += meta["n_samples_valid"]
        audit["samples_excluded_structure"] += meta["n_samples_excluded_structure"]
        audit["samples_retained"] += meta["n_samples_used"]
        if meta["modal_k_tie"]:
            audit["runs_with_tied_modal_k"].append({
                "run_id": run_dir.name,
                "candidates": meta["modal_k_candidates"],
                "selected_k": meta["modal_k"],
                "consensus": meta["modal_k_consensus"],
            })
        if meta["n_samples_used"] % 2 == 0:
            audit["runs_with_even_retained_samples"].append(run_dir.name)
        if meta["n_cell_vote_ties"]:
            audit["cell_vote_ties_by_run"][run_dir.name] = meta["n_cell_vote_ties"]
        audit["successful_api_calls"] += config.get("token_cost", {}).get("calls", 0)
        audit["temperature_fallbacks"] += config.get("temperature_fallbacks", 0)
        for exclusion in meta["excluded_samples"]:
            structural_exclusions.append({
                "model": model,
                "run_id": run_dir.name,
                **exclusion,
            })

        violations = validate_run(run_dir)
        if violations:
            raise RuntimeError(f"rebuilt run is invalid: {run_dir}: {violations}")
        rebuilt.append(run_dir)
        print(
            f"REBUILT {run_dir.name} K={len(skills)} "
            f"valid/used={meta['n_samples_valid']}/{meta['n_samples_used']} "
            f"cell_ties={meta['n_cell_vote_ties']}"
        )

    audit_models = {}
    for model, values in sorted(model_audit.items()):
        successful = values["samples_successful"]
        retained = values["samples_retained"]
        audit_models[model] = {
            **{
                key: value for key, value in values.items()
                if key not in {
                    "input_k_distribution", "valid_k_distribution",
                    "final_k_distribution"
                }
            },
            "input_k_distribution": {
                str(k): count for k, count in sorted(values["input_k_distribution"].items())
            },
            "valid_k_distribution": {
                str(k): count for k, count in sorted(values["valid_k_distribution"].items())
            },
            "final_k_distribution": {
                str(k): count for k, count in sorted(values["final_k_distribution"].items())
            },
            "samples_retained_rate": round(retained / successful, 4),
        }

    audit_report = {
        "aggregation_version": "phase2-v2",
        "rules": {
            "structure": "exclude constituent samples with structural errors",
            "modal_k": "highest frequency, then highest aligned within-K consensus, then lower K",
            "medoid": "highest aligned agreement, then content hash",
            "cell_vote_tie": "use the aligned medoid sample value",
        },
        "runs": len(rebuilt),
        "samples_expected": sum(v["samples_expected"] for v in audit_models.values()),
        "samples_successful": sum(v["samples_successful"] for v in audit_models.values()),
        "samples_excluded_structure": len(structural_exclusions),
        "runs_with_tied_modal_k": sum(
            len(v["runs_with_tied_modal_k"]) for v in audit_models.values()
        ),
        "runs_with_even_retained_samples": sum(
            len(v["runs_with_even_retained_samples"]) for v in audit_models.values()
        ),
        "runs_with_cell_vote_ties": sum(
            len(v["cell_vote_ties_by_run"]) for v in audit_models.values()
        ),
        "total_cell_vote_ties": sum(
            sum(v["cell_vote_ties_by_run"].values()) for v in audit_models.values()
        ),
        "order_independence_checks": order_independence_checked,
        "order_independence_failures": 0,
        "recomputation": {
            "final_qmatrix_mismatches": qmatrix_mismatches,
            "final_codebook_mismatches": codebook_mismatches,
        },
        "models": audit_models,
        "structural_exclusions": structural_exclusions,
    }
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit_report, indent=2) + "\n")
    print(f"WROTE   {audit_path}")

    if args.evaluate:
        _items, expert_skills, expert_matrix = load_qmatrix(args.expert_q)
        expert = (expert_skills, expert_matrix)
        cache_dir = Path(args.per_run_cache)
        for run_dir in rebuilt:
            config = json.loads((run_dir / "config.json").read_text())
            print(f"EVALUATE {run_dir.name}")
            evaluate_one_run(
                run_dir,
                config["dataset"],
                expert,
                cache_dir,
                force=True,
            )

    print(f"Rebuilt {len(rebuilt)} B3 runs with phase2-v2 aggregation")


if __name__ == "__main__":
    main()
