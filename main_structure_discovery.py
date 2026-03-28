from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from src.io_utils import ensure_dir, read_jsonl, write_json, write_jsonl
from src.reasoning_card import build_reasoning_card
from src.scaffold_brief import build_scaffold_brief

JsonDict = Dict[str, Any]


def _infer_domain(dossiers: List[JsonDict]) -> str:
    for dossier in dossiers:
        item = dossier.get("item", {}) if isinstance(dossier.get("item"), dict) else {}
        for key in ["domain", "subject", "dataset", "source"]:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return "unknown_domain"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build reasoning cards and a scaffold brief from verified dossiers."
    )
    parser.add_argument(
        "--input",
        default="outputs/step2_verifier_verified_item_dossiers.jsonl",
        help="Verified dossiers JSONL",
    )
    parser.add_argument(
        "--out_cards",
        default="outputs/step2_5_reasoning_cards.jsonl",
        help="Reasoning cards JSONL",
    )
    parser.add_argument(
        "--out_scaffold",
        default="outputs/step2_5_scaffold_brief.json",
        help="Scaffold brief JSON",
    )
    parser.add_argument(
        "--out_candidates",
        default="outputs/step2_5_cluster_candidates.json",
        help="Cluster candidate summary JSON",
    )
    parser.add_argument(
        "--domain",
        default=None,
        help="Optional domain override",
    )
    parser.add_argument(
        "--target_k",
        type=int,
        default=None,
        help="Optional target number of scaffold clusters",
    )
    parser.add_argument(
        "--max_clusters",
        type=int,
        default=8,
        help="Maximum clusters when target_k is not set",
    )
    parser.add_argument(
        "--min_cluster_size",
        type=int,
        default=2,
        help="Minimum cluster size before heuristic merging",
    )
    args = parser.parse_args()

    load_dotenv(override=False)

    for path in [args.out_cards, args.out_scaffold, args.out_candidates]:
        ensure_dir(str(Path(path).parent))

    dossiers = read_jsonl(args.input)
    cards = [build_reasoning_card(dossier) for dossier in dossiers]
    write_jsonl(args.out_cards, cards)

    domain = args.domain or _infer_domain(dossiers)
    scaffold = build_scaffold_brief(
        cards=cards,
        domain=domain,
        target_k=args.target_k,
        max_clusters=args.max_clusters,
        min_cluster_size=args.min_cluster_size,
    )
    write_json(args.out_scaffold, scaffold)

    candidates = {
        "method": "heuristic_reasoning_signature_grouping",
        "input_count": len(cards),
        "target_k": args.target_k,
        "max_clusters": args.max_clusters,
        "min_cluster_size": args.min_cluster_size,
        "selected_partition": {
            "proposed_k": scaffold.get("proposed_k"),
            "cluster_sizes": {
                cluster["cluster_id"]: len(cluster.get("item_ids", []))
                for cluster in scaffold.get("clusters", [])
            },
        },
        "notes": [
            "This stage is currently a deterministic structural baseline.",
            "Replace or augment with embedding-based clustering in future iterations.",
        ],
    }
    write_json(args.out_candidates, candidates)

    print(f"Reasoning cards saved to: {args.out_cards}")
    print(f"Scaffold brief saved to: {args.out_scaffold}")
    print(f"Cluster candidates saved to: {args.out_candidates}")
    print(f"Proposed scaffold K: {scaffold.get('proposed_k')}")


if __name__ == "__main__":
    main()
