from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from src.cluster_transformer import ClusterTransformer, summarize_dossiers_for_transform
from src.io_utils import ensure_dir, read_json, read_jsonl, write_json
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]


def run_transformer(
    expert_id: str,
    scaffold_brief: JsonDict,
    dossiers_summary: List[JsonDict],
) -> JsonDict:
    llm = LLMClient()
    transformer = ClusterTransformer(llm=llm, expert_id=expert_id)
    return transformer.transform(
        scaffold_brief=scaffold_brief,
        dossiers_summary=dossiers_summary,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run cluster transformation review over a scaffold brief."
    )
    parser.add_argument(
        "--input",
        default="outputs/step2_verifier_verified_item_dossiers.jsonl",
        help="Verified dossiers JSONL",
    )
    parser.add_argument(
        "--scaffold_brief",
        default="outputs/step2_5_scaffold_brief.json",
        help="Scaffold brief JSON",
    )
    parser.add_argument(
        "--out",
        default="outputs/step2_6_cluster_transformations.json",
        help="Transformation outputs JSON",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Run transformer experts in parallel (default: True)",
    )
    args = parser.parse_args()

    load_dotenv(override=False)
    ensure_dir(str(Path(args.out).parent))
    Path(args.out).unlink(missing_ok=True)

    dossiers = read_jsonl(args.input)
    scaffold_brief = read_json(args.scaffold_brief)
    dossiers_summary = summarize_dossiers_for_transform(dossiers)
    expert_ids = ["A", "B", "C"]

    outputs: Dict[str, JsonDict] = {}
    if args.parallel:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(run_transformer, eid, scaffold_brief, dossiers_summary): eid
                for eid in expert_ids
            }
            for future in as_completed(futures):
                eid = futures[future]
                outputs[eid] = future.result()
                print(f"  ✓ Transformer {eid} completed")
    else:
        for eid in expert_ids:
            outputs[eid] = run_transformer(eid, scaffold_brief, dossiers_summary)
            print(f"  ✓ Transformer {eid} completed")

    write_json(args.out, outputs)
    print(f"Cluster transformations saved to: {args.out}")


if __name__ == "__main__":
    main()
