from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Sequence

from schemas.scaffold_brief import ScaffoldBrief
from src.structure_discovery import labels_to_clusters

JsonDict = Dict[str, Any]


def _title_from_tags_and_terms(tags: list[str], terms: list[str]) -> str:
    if tags:
        return " + ".join(tag.replace("_", " ").title() for tag in tags[:2])
    if terms:
        return " / ".join(term.replace("_", " ").title() for term in terms[:3])
    return "Mixed Reasoning Pattern"


def _cluster_operation_tags(cards: Sequence[JsonDict], members: Sequence[int], *, top_n: int = 4) -> list[str]:
    counter: Counter[str] = Counter()
    for idx in members:
        counter.update(cards[idx].get("operation_tags", []))
    return [tag for tag, _ in counter.most_common(top_n)]


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
    cluster_tags: list[str],
    cluster_terms: list[str],
    all_cluster_info: list[JsonDict],
    cluster_size: int,
) -> list[str]:
    notes: list[str] = []
    if cluster_size <= 2:
        notes.append("Small cluster; inspect whether it should merge with a nearby cluster.")
    if len(cluster_tags) <= 1:
        notes.append("Low tag diversity; inspect whether this cluster hides subskills.")

    tag_set = set(cluster_tags)
    term_set = set(cluster_terms)
    best_neighbor = None
    best_overlap = 0
    for info in all_cluster_info:
        if info["cluster_id"] == cluster_id:
            continue
        overlap = len(tag_set & set(info.get("operation_tags", []))) + len(term_set & set(info.get("top_terms", [])))
        if overlap > best_overlap:
            best_overlap = overlap
            best_neighbor = info
    if best_neighbor is not None and best_overlap > 0:
        notes.append(
            f"Potential boundary overlap with {best_neighbor['cluster_id']} via shared tags/terms; compare definitions before finalizing."
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

    provisional_info: list[JsonDict] = []
    for order, (label, members) in enumerate(sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0])), start=1):
        cluster_id = f"C{order:02d}"
        terms = list(top_terms_map.get(str(label), []))
        tags = _cluster_operation_tags(cards, members)
        provisional_info.append(
            {
                "cluster_id": cluster_id,
                "label": label,
                "members": members,
                "top_terms": terms,
                "operation_tags": tags,
                "provisional_skill_name": _title_from_tags_and_terms(tags, terms),
            }
        )

    clusters: list[JsonDict] = []
    for info in provisional_info:
        members = info["members"]
        cluster_id = info["cluster_id"]
        boundary_notes = _boundary_notes(
            cluster_id=cluster_id,
            cluster_tags=info["operation_tags"],
            cluster_terms=info["top_terms"],
            all_cluster_info=provisional_info,
            cluster_size=len(members),
        )
        clusters.append(
            {
                "cluster_id": cluster_id,
                "provisional_skill_name": info["provisional_skill_name"],
                "rationale": (
                    "Derived from hierarchical clustering over reasoning-card TF-IDF representations, "
                    "then summarized with dominant operation tags and top cluster terms."
                ),
                "operation_tags": info["operation_tags"],
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
            "Selected candidate metrics — overall: {overall}, stability: {stability}, silhouette: {silhouette}, interpretability: {interpretability}.".format(
                overall=metrics.get("overall"),
                stability=metrics.get("stability"),
                silhouette=metrics.get("silhouette"),
                interpretability=metrics.get("interpretability"),
            )
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
