"""
Official structure discovery runner.

This is the recommended entrypoint for scaffold construction.
It defaults to embedding-based clustering over reasoning cards and can optionally
fall back to the TF-IDF hierarchical clustering backend when embeddings are not
available or when the embedding call fails.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from src.cluster_selection import select_candidate_by_k, summarize_candidate_table
from src.io_utils import ensure_dir, read_jsonl, write_json, write_jsonl
from src.reasoning_card import build_reasoning_card
from src.scaffold_from_clusters import build_scaffold_brief_from_candidate
from src.structure_discovery import search_candidate_partitions
from src.structure_discovery_embed import search_candidate_partitions_embed

JsonDict = Dict[str, Any]


def _infer_domain(dossiers: List[JsonDict]) -> str:
    for dossier in dossiers:
        item = dossier.get("item", {}) if isinstance(dossier.get("item"), dict) else {}
        for key in ["domain", "subject", "dataset", "source"]:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return "unknown_domain"


def _select_candidate(candidates: List[JsonDict], target_k: int | None) -> JsonDict:
    selected_candidate = None
    if target_k is not None:
        selected_candidate = select_candidate_by_k(candidates, target_k)
    if selected_candidate is None and candidates:
        selected_candidate = dict(candidates[0])
    if selected_candidate is None:
        raise RuntimeError("No candidate partition was generated.")
    return selected_candidate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Official embedding-first structure discovery runner."
    )
    parser.add_argument("--input", default="outputs/step2_verifier_verified_item_dossiers.jsonl", help="Verified dossiers JSONL")
    parser.add_argument("--out_cards", default="outputs/step2_5_reasoning_cards.jsonl", help="Reasoning cards JSONL")
    parser.add_argument("--out_scaffold", default="outputs/step2_5_scaffold_brief.json", help="Scaffold brief JSON")
    parser.add_argument("--out_candidates", default="outputs/step2_5_cluster_candidates.json", help="Candidate K summary JSON")
    parser.add_argument("--domain", default=None, help="Optional domain override")
    parser.add_argument("--min_k", type=int, default=3, help="Minimum candidate K to evaluate")
    parser.add_argument("--max_k", type=int, default=8, help="Maximum candidate K to evaluate")
    parser.add_argument("--target_k", type=int, default=None, help="Optional fixed K override after candidate search")
    parser.add_argument("--embedding_model", default=None, help="Optional embedding model override. Defaults to OPENAI_EMBEDDING_MODEL.")
    parser.add_argument("--fallback_method", choices=["none", "tfidf"], default="tfidf", help="Fallback method when embedding-based search fails")
    parser.add_argument("--force_method", choices=["auto", "embedding", "tfidf"], default="auto", help="Force a specific structure discovery backend")
    args = parser.parse_args()

    load_dotenv(override=False)

    for path in [args.out_cards, args.out_scaffold, args.out_candidates]:
        ensure_dir(str(Path(path).parent))

    dossiers = read_jsonl(args.input)
    cards = [build_reasoning_card(dossier) for dossier in dossiers]
    write_jsonl(args.out_cards, cards)

    domain = args.domain or _infer_domain(dossiers)
    backend = "embedding"
    search_output: JsonDict | None = None
    backend_note = ""

    if args.force_method == "tfidf":
        backend = "tfidf"
        search_output = search_candidate_partitions(cards, min_k=args.min_k, max_k=args.max_k)
        backend_note = "TF-IDF backend forced by user."
    else:
        try:
            if args.force_method in {"auto", "embedding"}:
                search_output = search_candidate_partitions_embed(
                    cards,
                    embedding_model=args.embedding_model,
                    min_k=args.min_k,
                    max_k=args.max_k,
                )
                backend = "embedding"
                backend_note = "Embedding-based clustering succeeded."
        except Exception as exc:
            if args.force_method == "embedding" or args.fallback_method == "none":
                raise RuntimeError(f"Embedding-based structure discovery failed: {exc}") from exc
            backend = "tfidf"
            search_output = search_candidate_partitions(cards, min_k=args.min_k, max_k=args.max_k)
            backend_note = f"Embedding-based clustering failed; fell back to TF-IDF backend. Error: {exc}"

    if search_output is None:
        raise RuntimeError("Structure discovery did not produce search output.")

    candidates = search_output.get("candidates", [])
    selected_candidate = _select_candidate(candidates, args.target_k)

    scaffold = build_scaffold_brief_from_candidate(cards=cards, domain=domain, candidate=selected_candidate)
    write_json(args.out_scaffold, scaffold)

    candidate_payload = {
        "method": "embedding_reasoning_card_hierarchical_clustering" if backend == "embedding" else "tfidf_reasoning_card_hierarchical_clustering",
        "backend": backend,
        "backend_note": backend_note,
        "input_count": len(cards),
        "search_range": {"min_k": args.min_k, "max_k": args.max_k},
        "target_k": args.target_k,
        "embedding_model": args.embedding_model,
        "candidate_table": summarize_candidate_table(candidates),
        "selected_candidate": {
            "k": selected_candidate.get("k"),
            "metrics": selected_candidate.get("metrics", {}),
            "cluster_sizes": selected_candidate.get("cluster_sizes", []),
        },
        "notes": [
            "Reasoning cards combine item stem, solution summary, step traces, and inferred operation tags.",
            "Final skill count can differ from selected cluster K after expert/supervisor refinement.",
            "This is the official structure discovery entrypoint for the scaffold pipeline.",
        ],
    }
    write_json(args.out_candidates, candidate_payload)

    print(f"Reasoning cards saved to: {args.out_cards}")
    print(f"Candidate table saved to: {args.out_candidates}")
    print(f"Scaffold brief saved to: {args.out_scaffold}")
    print(f"Selected cluster K: {selected_candidate.get('k')}")
    print(f"Structure discovery backend: {backend}")


if __name__ == "__main__":
    main()
