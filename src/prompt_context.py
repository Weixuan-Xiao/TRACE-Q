"""Unified prompt context builders for taxonomist stages.

Each function merges scaffold + consensus/transformation info into a single
compact text block so that LLM agents see each cluster exactly once.
"""
from __future__ import annotations

from typing import Any, Dict, List

JsonDict = Dict[str, Any]


# ---------------------------------------------------------------------------
# Scaffold-only (used by main_taxonomist_scaffold.py)
# ---------------------------------------------------------------------------

def build_scaffold_only_context_text(scaffold: JsonDict) -> str:
    """Compact prompt block from scaffold brief alone."""
    lines: list[str] = [
        "STRUCTURE DISCOVERY SCAFFOLD",
        f"Proposed K: {scaffold.get('proposed_k', '?')}",
        "Use this scaffold as a shared starting point. You may keep, merge, "
        "split, or relabel clusters, but explain departures.",
        "",
    ]
    for cluster in scaffold.get("clusters", []):
        cid = cluster.get("cluster_id", "?")
        name = cluster.get("provisional_skill_name", "?")
        tags = ", ".join(cluster.get("distinguishing_terms", []))
        items = ", ".join(cluster.get("item_ids", [])[:6])
        line = f"- {cid}: {name}"
        if tags:
            line += f" (terms: {tags})"
        lines.append(line)
        if items:
            lines.append(f"  items: {items}")
        for note in cluster.get("boundary_notes", [])[:2]:
            lines.append(f"  note: {note}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scaffold + transformation outputs (used by main_taxonomist_transform.py)
# ---------------------------------------------------------------------------

def build_scaffold_transform_context_text(
    scaffold: JsonDict,
    transform_outputs: List[JsonDict],
) -> str:
    """Merge scaffold clusters with raw transformation decisions into one block."""
    # Index transformation decisions by cluster_id
    decision_map: dict[str, list[JsonDict]] = {}
    for output in transform_outputs:
        eid = output.get("expert_id", "?")
        for decision in output.get("decisions", []):
            cid = decision.get("cluster_id", "")
            decision_map.setdefault(cid, []).append({**decision, "_expert": eid})

    lines: list[str] = [
        "STRUCTURE DISCOVERY & TRANSFORMATION REVIEW",
        f"Proposed K: {scaffold.get('proposed_k', '?')}",
        "",
    ]

    for cluster in scaffold.get("clusters", []):
        cid = cluster.get("cluster_id", "?")
        name = cluster.get("provisional_skill_name", "?")
        tags = ", ".join(cluster.get("distinguishing_terms", []))
        items = ", ".join(cluster.get("item_ids", [])[:6])

        # Build action summary from transformer decisions
        decisions = decision_map.get(cid, [])
        if decisions:
            action_parts = []
            for d in decisions:
                action_parts.append(f"{d['_expert']}={d.get('action', '?')}")
            action_str = " ".join(action_parts)
            lines.append(f"- {cid} [{action_str}]: {name}")
        else:
            lines.append(f"- {cid}: {name}")

        if tags:
            lines.append(f"  terms: {tags}")
        if items:
            lines.append(f"  items: {items}")
        # Show proposed names from transformers (deduplicated)
        proposed = []
        for d in decisions:
            proposed.extend(d.get("proposed_skill_names", []))
        unique_names = list(dict.fromkeys(n for n in proposed if n))
        if unique_names:
            lines.append(f"  proposed names: {', '.join(unique_names[:3])}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scaffold + consensus (used by main_taxonomist_consensus.py)
# ---------------------------------------------------------------------------

def build_unified_context_text(
    scaffold: JsonDict,
    consensus: JsonDict,
) -> str:
    """Merge scaffold brief and transformation consensus into one prompt block.

    Each cluster appears exactly once with scaffold info (name, tags, items)
    and consensus info (action, agreement, proposed names) combined.
    """
    # Index consensus decisions by cluster_id
    consensus_map: dict[str, JsonDict] = {}
    for decision in consensus.get("consensus_decisions", []):
        cid = decision.get("cluster_id", "")
        if cid:
            consensus_map[cid] = decision

    recommended_k = consensus.get("recommended_final_k", scaffold.get("proposed_k", "?"))

    lines: list[str] = [
        "STRUCTURE DISCOVERY & CONSENSUS BRIEF",
        f"Recommended K: {recommended_k}",
        "",
    ]

    for cluster in scaffold.get("clusters", []):
        cid = cluster.get("cluster_id", "?")
        name = cluster.get("provisional_skill_name", "?")
        tags = ", ".join(cluster.get("distinguishing_terms", []))
        items = ", ".join(cluster.get("item_ids", [])[:6])
        cd = consensus_map.get(cid)

        # Header: cluster id + consensus action + scaffold name
        if cd:
            action = cd.get("consensus_action", "?").upper()
            agreement = cd.get("agreement", "?")
            targets = cd.get("target_cluster_ids", [])
            if action == "MERGE" and targets:
                header = f"- {cid} [{action}→{','.join(targets[:3])} {agreement}]: {name}"
            else:
                header = f"- {cid} [{action} {agreement}]: {name}"
        else:
            header = f"- {cid}: {name}"
        if tags:
            header += f" (terms: {tags})"
        lines.append(header)

        if items:
            lines.append(f"  items: {items}")

        # Consensus proposed names (if different from scaffold name)
        if cd:
            proposed = cd.get("proposed_skill_names", [])
            unique = [n for n in proposed if n and n != name]
            if unique:
                lines.append(f"  proposed name: {', '.join(unique[:2])}")

        # Boundary notes from scaffold
        for note in cluster.get("boundary_notes", [])[:1]:
            lines.append(f"  note: {note}")

        # Action hint from consensus notes
        if cd:
            for note in cd.get("notes", [])[:1]:
                lines.append(f"  → {note}")

    # Draft skill candidates
    drafts = consensus.get("draft_skill_candidates", [])
    if drafts:
        lines.append("")
        lines.append("Draft skill candidates:")
        for draft in drafts[:10]:
            dname = draft.get("name", "?")
            support = draft.get("support_count", 0)
            src = ", ".join(draft.get("source_cluster_ids", []))
            lines.append(f"- {dname} [support={support}; from {src}]")

    return "\n".join(lines)
