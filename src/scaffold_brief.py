"""TF-IDF fallback path for scaffold brief construction.

Used when embedding-based structure discovery is unavailable.
Groups reasoning cards by TF-IDF similarity, then builds a scaffold brief.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List

from schemas.scaffold_brief import ScaffoldBrief
from src.structure_discovery import (
    _tokenize,
    card_to_document,
    cluster_distinguishing_terms,
)

JsonDict = Dict[str, Any]


def _title_from_terms(terms: list[str]) -> str:
    if not terms:
        return "Mixed Reasoning Pattern"
    return " / ".join(term.replace("_", " ").title() for term in terms[:3])


def _merge_small_clusters(
    grouped: Dict[int, List[int]],
    raw_counts: List[Counter[str]],
    *,
    target_k: int | None,
    max_clusters: int,
    min_cluster_size: int,
) -> Dict[int, List[int]]:
    """Merge smallest clusters into most similar neighbor based on term overlap."""
    grouped = {k: list(v) for k, v in grouped.items()}

    def current_limit() -> int:
        if target_k is not None and target_k > 0:
            return target_k
        return max_clusters

    def _cluster_terms(members: List[int]) -> set[str]:
        terms: set[str] = set()
        for idx in members:
            terms.update(raw_counts[idx].keys())
        return terms

    while True:
        too_many = len(grouped) > current_limit()
        too_small = any(len(v) < min_cluster_size for v in grouped.values()) and len(grouped) > 1
        if not too_many and not too_small:
            break

        smallest_key = min(grouped, key=lambda key: (len(grouped[key]), key))
        smallest_terms = _cluster_terms(grouped[smallest_key])
        candidate_keys = [k for k in grouped if k != smallest_key]
        if not candidate_keys:
            break

        def score(other_key: int) -> tuple[int, int, int]:
            other_terms = _cluster_terms(grouped[other_key])
            overlap = len(smallest_terms & other_terms)
            union = len(smallest_terms | other_terms)
            return (-overlap, union, other_key)

        best_key = sorted(candidate_keys, key=score)[0]
        grouped[best_key].extend(grouped.pop(smallest_key))

    return grouped


def group_reasoning_cards(
    cards: Iterable[JsonDict],
    *,
    target_k: int | None = None,
    max_clusters: int = 8,
    min_cluster_size: int = 2,
) -> Dict[int, List[int]]:
    """Group reasoning cards by TF-IDF token similarity.

    Returns {cluster_label: [card_indices]}.
    """
    cards_list = list(cards)
    if not cards_list:
        return {}

    # Build raw token counts
    raw_counts: List[Counter[str]] = []
    for card in cards_list:
        raw_counts.append(Counter(_tokenize(card_to_document(card))))

    # Start with each card in its own cluster, then merge
    # Simple approach: group by most frequent non-stopword token
    token_groups: Dict[str, List[int]] = defaultdict(list)
    for idx, counts in enumerate(raw_counts):
        top_token = counts.most_common(1)[0][0] if counts else "misc"
        token_groups[top_token].append(idx)

    grouped = {i: members for i, members in enumerate(token_groups.values())}
    grouped = _merge_small_clusters(
        grouped,
        raw_counts,
        target_k=target_k,
        max_clusters=max_clusters,
        min_cluster_size=min_cluster_size,
    )
    return grouped


def build_scaffold_brief(
    *,
    cards: List[JsonDict],
    domain: str,
    target_k: int | None = None,
    max_clusters: int = 8,
    min_cluster_size: int = 2,
) -> JsonDict:
    grouped = group_reasoning_cards(
        cards,
        target_k=target_k,
        max_clusters=max_clusters,
        min_cluster_size=min_cluster_size,
    )

    # Build raw counts for distinguishing term extraction
    raw_counts: List[Counter[str]] = []
    for card in cards:
        raw_counts.append(Counter(_tokenize(card_to_document(card))))

    all_members_list = [
        members for _, members in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    ]

    clusters: List[JsonDict] = []
    ordered_groups = sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    for idx, (_label, members) in enumerate(ordered_groups, start=1):
        dist_terms = cluster_distinguishing_terms(
            members, raw_counts, all_members_list, top_n=5,
        )

        representative_items = []
        for card_idx in members[:3]:
            card = cards[card_idx]
            representative_items.append({
                "item_id": str(card.get("item_id", "")),
                "step_ids": [],
                "note": str(card.get("solution_summary", ""))[:180],
            })

        boundary_notes: List[str] = []
        if len(members) <= min_cluster_size:
            boundary_notes.append(
                "Small cluster; inspect whether it should merge with a nearby cluster."
            )

        clusters.append({
            "cluster_id": f"C{idx:02d}",
            "provisional_skill_name": _title_from_terms(dist_terms),
            "rationale": (
                "Grouped by TF-IDF token similarity over reasoning card texts, "
                "then named using cluster-vs-corpus distinguishing terms."
            ),
            "distinguishing_terms": dist_terms,
            "representative_items": representative_items,
            "boundary_notes": boundary_notes,
            "item_ids": [str(cards[i].get("item_id", "")) for i in members],
        })

    brief = ScaffoldBrief(
        version="v1",
        domain=domain,
        source_stage="structure_discovery",
        proposed_k=len(clusters),
        clusters=clusters,
        global_notes=[
            "This scaffold is a TF-IDF fallback derived from reasoning-card token patterns.",
            "Final skill count may differ from proposed_k after expert keep/merge/split/relabel decisions.",
        ],
    )
    return brief.model_dump()


def scaffold_brief_to_prompt_text(brief: JsonDict) -> str:
    """Legacy prompt text builder — kept for backward compatibility."""
    lines: List[str] = []
    lines.append("STRUCTURE DISCOVERY SCAFFOLD")
    lines.append(f"Proposed K: {brief.get('proposed_k', '?')}")
    lines.append("Use this scaffold as a shared starting point. You may keep, merge, split, or relabel clusters, but you must explain departures from the scaffold.")
    for cluster in brief.get("clusters", []):
        cid = cluster.get("cluster_id", "?")
        name = cluster.get("provisional_skill_name", "?")
        terms = ", ".join(cluster.get("distinguishing_terms", cluster.get("operation_tags", [])))
        item_ids = ", ".join(cluster.get("item_ids", [])[:6])
        lines.append(f"- {cid}: {name}")
        if terms:
            lines.append(f"  terms: {terms}")
        if item_ids:
            lines.append(f"  example items: {item_ids}")
        boundary_notes = cluster.get("boundary_notes", [])
        for note in boundary_notes[:2]:
            lines.append(f"  boundary note: {note}")
    return "\n".join(lines)
