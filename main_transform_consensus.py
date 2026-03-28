from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from src.io_utils import ensure_dir, read_json, write_json
from src.transform_consensus import build_transform_consensus

JsonDict = Dict[str, Any]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a structured consensus layer from cluster transformation outputs."
    )
    parser.add_argument(
        "--scaffold_brief",
        default="outputs/step2_5_scaffold_brief.json",
        help="Scaffold brief JSON",
    )
    parser.add_argument(
        "--transformations",
        default="outputs/step2_6_cluster_transformations.json",
        help="Transformer outputs JSON",
    )
    parser.add_argument(
        "--out",
        default="outputs/step2_7_transform_consensus.json",
        help="Consensus output JSON",
    )
    args = parser.parse_args()

    load_dotenv(override=False)
    ensure_dir(str(Path(args.out).parent))
    Path(args.out).unlink(missing_ok=True)

    scaffold_brief = read_json(args.scaffold_brief)
    transform_raw = read_json(args.transformations)
    transform_outputs = [transform_raw[key] for key in sorted(transform_raw)] if isinstance(transform_raw, dict) else []

    consensus = build_transform_consensus(
        scaffold_brief=scaffold_brief,
        transform_outputs=transform_outputs,
    )
    write_json(args.out, consensus)
    print(f"Transformation consensus saved to: {args.out}")
    print(f"Recommended final K: {consensus.get('recommended_final_k')}")
    print(f"Disputed clusters: {len(consensus.get('disputed_clusters', []))}")


if __name__ == "__main__":
    main()
