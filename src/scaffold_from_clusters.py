from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Sequence

from schemas.scaffold_brief import ScaffoldBrief
from src.structure_discovery import (
    _tokenize,
    card_to_document,
    cluster_distinguishing_terms,
    labels_to_clusters,
)

JsonDict = Dict[str, Any]


def _title_from_terms(terms: list[str]) -> str:
    """Generate a readable cluster title from distinguishing terms."""
    if not terms:
        return "Mixed Reasoning Pattern"
    return " / ".join(term.replace("_", " ").title() for term in terms[:3])


def _representative_items(cards: Sequence[JsonDict], members: Sequence[int], *, top_n: int = 3) -> list[JsonDict]:
    reps: list[JsonDict] = []
    for idx in list(members)[:top_n]:
        card = cards[idx]
        reps.append(
            {
                "item_id": str(card.get("item_id", "")),
                "step_ids": [],
                "note": str(card.get("solution_summary", ""))[:180],
            }
        )
    return reps


def _boundary_notes(
    *,
    cluster_id: str,
    cluster_terms: list[str],
    all_cluster_info: list[JsonDict],
    cluster_size: int,
) -> list[str]:
    notes: list[str] = []
    if cluster_size <= 2:
        notes.append("Small cluster; inspect whether it should merge with a nearby cluster.")

    term_set = set(cluster_terms)
    best_neighbor = None
    best_overlap = 0
    for info in all_cluster_info:
        if info["cluster_id"] == cluster_id:
            continue
        overlap = len(term_set & set(info.get("distinguishing_terms", [])))
        if overlap > best_overlap:
            best_overlap = overlap
            best_neighbor = info
    if best_neighbor is not None and best_overlap > 0:
        notes.append(
            f"Potential boundary overlap with {best_neighbor['cluster_id']} via shared terms; compare definitions before finalizing."
        )
    return notes


def build_scaffold_brief_from_candidate(
    *,
    cards: Sequence[JsonDict],
    domain: str,
    candidate: JsonDict,
) -> JsonDict:
    labels = candidate.get("labels", [])
    top_terms_map = candidate.get("top_terms", {})
    grouped = labels_to_clusters(labels)

    # Build per-card raw token counts for distinguishing-term extraction
    raw_counts: list[Counter[str]] = []
    for card in cards:
        raw_counts.append(Counter(_tokenize(card_to_document(card))))

    all_members_list = [
        members for _, members in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    ]

    provisional_info: list[JsonDict] = []
    for order, (label, members) in enumerate(sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0])), start=1):
        cluster_id = f"C{order:02d}"
        # Two-layer naming: distinguishing terms + readable title
        dist_terms = cluster_distinguishing_terms(
            members, raw_counts, all_members_list, top_n=5,
        )
        # Fall back to simple top_terms if distinguishing terms are sparse
        if len(dist_terms) < 2:
            dist_terms = list(top_terms_map.get(str(label), []))[:5]
        provisional_info.append(
            {
                "cluster_id": cluster_id,
                "label": label,
                "members": members,
                "distinguishing_terms": dist_terms,
                "provisional_skill_name": _title_from_terms(dist_terms),
            }
        )

    clusters: list[JsonDict] = []
    for info in provisional_info:
        members = info["members"]
        cluster_id = info["cluster_id"]
        boundary_notes = _boundary_notes(
            cluster_id=cluster_id,
            cluster_terms=info["distinguishing_terms"],
            all_cluster_info=provisional_info,
            cluster_size=len(members),
        )
        clusters.append(
            {
                "cluster_id": cluster_id,
                "provisional_skill_name": info["provisional_skill_name"],
                "rationale": (
                    "Derived from hierarchical clustering over reasoning-card embeddings, "
                    "then named using cluster-vs-corpus distinguishing terms."
                ),
                "distinguishing_terms": info["distinguishing_terms"],
                "representative_items": _representative_items(cards, members),
                "boundary_notes": boundary_notes,
                "item_ids": [str(cards[idx].get("item_id", "")) for idx in members],
            }
        )

    global_notes = [
        "Clusters come from structure discovery over item + solution + step-trace representations.",
        "Use the scaffold as a shared starting point. Final skills may keep, merge, split, or relabel these clusters.",
    ]
    metrics = candidate.get("metrics", {})
    if metrics:
        global_notes.append(
            f"Selected candidate metrics — overall: {metrics.get('overall')}, "
            f"stability: {metrics.get('stability')}, silhouette: {metrics.get('silhouette')}, "
            f"interpretability: {metrics.get('interpretability')}."
        )

    brief = ScaffoldBrief(
        version="v1",
        domain=domain,
        source_stage="structure_discovery",
        proposed_k=int(candidate.get("k", len(clusters))),
        clusters=clusters,
        global_notes=global_notes,
    )
    return brief.model_dump()
