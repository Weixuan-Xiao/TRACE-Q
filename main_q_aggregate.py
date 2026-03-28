from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from src.codebook_utils import extract_skill_ids
from src.io_utils import ensure_dir, read_json, write_json, write_jsonl
from src.q_aggregate import collect_vote_matrix, finalize_q_matrix, load_vote_rows

JsonDict = Dict[str, Any]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate tagger votes into a final Q-matrix and uncertainty reports."
    )
    parser.add_argument("--votes_dir", default="outputs/step4_tagger_votes_transform", help="Directory containing tagger vote JSONL files")
    parser.add_argument("--codebook", default="outputs/step3_skill_codebook_consensus.json", help="Final codebook JSON")
    parser.add_argument("--out_q", default="outputs/step5_final_q_matrix.jsonl", help="Final Q-matrix JSONL")
    parser.add_argument("--out_cells", default="outputs/step5_cell_uncertainty.jsonl", help="Cell-level uncertainty JSONL")
    parser.add_argument("--out_items", default="outputs/step5_item_uncertainty.jsonl", help="Item-level uncertainty JSONL")
    parser.add_argument("--out_summary", default="outputs/step5_stability_summary.json", help="Overall stability summary JSON")
    parser.add_argument("--decision_threshold", type=float, default=0.5, help="Vote proportion threshold for assigning Q=1")
    args = parser.parse_args()

    load_dotenv(override=False)
    for path in [args.out_q, args.out_cells, args.out_items, args.out_summary]:
        ensure_dir(str(Path(path).parent))
        Path(path).unlink(missing_ok=True)

    rows = load_vote_rows(args.votes_dir)
    codebook = read_json(args.codebook)
    skill_ids = sorted(extract_skill_ids(codebook))

    matrix, ordered_skills = collect_vote_matrix(rows=rows, skill_ids=skill_ids)
    q_rows, cell_rows, item_rows, summary = finalize_q_matrix(
        matrix=matrix,
        skill_ids=ordered_skills,
        decision_threshold=args.decision_threshold,
    )

    write_jsonl(args.out_q, q_rows)
    write_jsonl(args.out_cells, cell_rows)
    write_jsonl(args.out_items, item_rows)
    write_json(args.out_summary, summary)

    print(f"Final Q-matrix saved to: {args.out_q}")
    print(f"Cell uncertainty report saved to: {args.out_cells}")
    print(f"Item uncertainty report saved to: {args.out_items}")
    print(f"Stability summary saved to: {args.out_summary}")
    print(f"Mean cell agreement: {summary.get('mean_cell_agreement')}")
    print(f"Disputed cells: {summary.get('num_disputed_cells')}")


if __name__ == "__main__":
    main()
