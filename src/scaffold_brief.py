from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List

from schemas.scaffold_brief import ScaffoldBrief

JsonDict = Dict[str, Any]


def _tags_from_signature(signature: str) -> list[str]:
    return [part for part in signature.split("|") if part]


def _title_from_tags(tags: list[str]) -> str:
    if not tags:
        return "Miscellaneous Reasoning"
    return " + ".join(tag.replace("_", " ").title() for tag in tags[:3])


def _merge_small_clusters(
    grouped: Dict[str, List[JsonDict]],
    *,
    target_k: int | None,
    max_clusters: int,
    min_cluster_size: int,
) -> Dict[str, List[JsonDict]]:
    grouped = {k: list(v) for k, v in grouped.items()}

    def current_limit() -> int:
        if target_k is not None and target_k > 0:
            return target_k
        return max_clusters

    while True:
        too_many = len(grouped) > current_limit()
        too_small = any(len(v) < min_cluster_size for v in grouped.values()) and len(grouped) > 1
        if not too_many and not too_small:
            break

        smallest_key = min(grouped, key=lambda key: (len(grouped[key]), key))
        smallest_tags = set(_tags_from_signature(smallest_key))
        candidate_keys = [k for k in grouped if k != smallest_key]
        if not candidate_keys:
            break

        def score(other_key: str) -> tuple[int, int, str]:
            other_tags = set(_tags_from_signature(other_key))
            overlap = len(smallest_tags & other_tags)
            union = len(smallest_tags | other_tags)
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
) -> Dict[str, List[JsonDict]]:
    grouped: Dict[str, List[JsonDict]] = defaultdict(list)
    for card in cards:
        signature = str(card.get("structural_signature", "")).strip() or "misc"
        grouped[signature].append(card)
    return _merge_small_clusters(
        grouped,
        target_k=target_k,
        max_clusters=max_clusters,
        min_cluster_size=min_cluster_size,
    )


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

    clusters: List[JsonDict] = []
    ordered_groups = sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    for idx, (signature, members) in enumerate(ordered_groups, start=1):
        tags = _tags_from_signature(signature)
        representative_items = []
        for card in members[:3]:
            representative_items.append({
                "item_id": str(card.get("item_id", "")),
                "step_ids": [],
                "note": card.get("solution_summary", "")[:180],
            })

        boundary_notes: List[str] = []
        if len(tags) == 1:
            boundary_notes.append(
                "Single dominant tag cluster; check for hidden subskills before finalizing."
            )
        if len(members) <= min_cluster_size:
            boundary_notes.append(
                "Small cluster; inspect whether it should merge with a nearby cluster."
            )

        clusters.append({
            "cluster_id": f"C{idx:02d}",
            "provisional_skill_name": _title_from_tags(tags),
            "rationale": (
                "Grouped by shared operation tags inferred from stem text, solution summary, "
                "and step patterns."
            ),
            "operation_tags": tags,
            "representative_items": representative_items,
            "boundary_notes": boundary_notes,
            "item_ids": [str(card.get("item_id", "")) for card in members],
        })

    brief = ScaffoldBrief(
        version="v1",
        domain=domain,
        source_stage="structure_discovery",
        proposed_k=len(clusters),
        clusters=clusters,
        global_notes=[
            "This scaffold is a deterministic baseline derived from reasoning-card signatures.",
            "Final skill count may differ from proposed_k after expert keep/merge/split/relabel decisions.",
        ],
    )
    return brief.model_dump()


def scaffold_brief_to_prompt_text(brief: JsonDict) -> str:
    lines: List[str] = []
    lines.append("STRUCTURE DISCOVERY SCAFFOLD")
    lines.append(f"Proposed K: {brief.get('proposed_k', '?')}")
    lines.append("Use this scaffold as a shared starting point. You may keep, merge, split, or relabel clusters, but you must explain departures from the scaffold.")
    for cluster in brief.get("clusters", []):
        cid = cluster.get("cluster_id", "?")
        name = cluster.get("provisional_skill_name", "?")
        tags = ", ".join(cluster.get("operation_tags", []))
        item_ids = ", ".join(cluster.get("item_ids", [])[:6])
        lines.append(f"- {cid}: {name}")
        if tags:
            lines.append(f"  tags: {tags}")
        if item_ids:
            lines.append(f"  example items: {item_ids}")
        boundary_notes = cluster.get("boundary_notes", [])
        for note in boundary_notes[:2]:
            lines.append(f"  boundary note: {note}")
    return "\n".join(lines)
