from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Tuple

from schemas.transform_consensus import TransformConsensus

JsonDict = Dict[str, Any]


def _normalize_name(name: str) -> str:
    return " ".join((name or "").strip().lower().split())


def _agreement_string(votes: list[str], winner: str) -> str:
    win = sum(1 for v in votes if v == winner)
    return f"{win}/{len(votes)}"


def _merge_targets(outputs: List[JsonDict], cluster_id: str, winner: str) -> list[str]:
    targets: Counter[str] = Counter()
    for output in outputs:
        for decision in output.get("decisions", []):
            if decision.get("cluster_id") != cluster_id:
                continue
            if decision.get("action") != winner:
                continue
            for target in decision.get("target_cluster_ids", []):
                if target and target != cluster_id:
                    targets[str(target)] += 1
    return [target for target, _ in targets.most_common()]


def _proposed_names(outputs: List[JsonDict], cluster_id: str, winner: str) -> list[str]:
    names: Counter[str] = Counter()
    for output in outputs:
        for decision in output.get("decisions", []):
            if decision.get("cluster_id") != cluster_id:
                continue
            if decision.get("action") != winner:
                continue
            for name in decision.get("proposed_skill_names", []):
                norm = str(name).strip()
                if norm:
                    names[norm] += 1
    return [name for name, _ in names.most_common()]


def build_transform_consensus(
    *,
    scaffold_brief: JsonDict,
    transform_outputs: List[JsonDict],
) -> JsonDict:
    clusters = [cluster.get("cluster_id", "") for cluster in scaffold_brief.get("clusters", [])]
    decisions_out: list[JsonDict] = []
    disputed: list[str] = []

    for cluster_id in clusters:
        votes: list[str] = []
        for output in transform_outputs:
            for decision in output.get("decisions", []):
                if decision.get("cluster_id") == cluster_id:
                    votes.append(str(decision.get("action", "")))
                    break

        vote_counts = Counter(votes)
        if not vote_counts:
            consensus_action = "disputed"
            winner = "disputed"
            agreement = "0/0"
        else:
            winner, winner_count = vote_counts.most_common(1)[0]
            agreement = _agreement_string(votes, winner)
            consensus_action = winner if winner_count >= 2 else "disputed"

        if consensus_action == "disputed":
            disputed.append(cluster_id)

        notes: list[str] = []
        if consensus_action == "merge":
            notes.append("Use merged cluster group as a draft structure before final codebook synthesis.")
        elif consensus_action == "split":
            notes.append("Do not treat this cluster as a stable one-to-one skill candidate.")
        elif consensus_action == "relabel":
            notes.append("Retain the cluster boundary but prefer the consensus relabel over the provisional scaffold title.")
        elif consensus_action == "keep":
            notes.append("This cluster is a stable draft skill candidate.")
        else:
            notes.append("High disagreement; route to expert/supervisor review as a disputed cluster.")

        decisions_out.append(
            {
                "cluster_id": cluster_id,
                "consensus_action": consensus_action,
                "agreement": agreement,
                "vote_counts": dict(vote_counts),
                "target_cluster_ids": _merge_targets(transform_outputs, cluster_id, winner),
                "proposed_skill_names": _proposed_names(transform_outputs, cluster_id, winner),
                "notes": notes,
            }
        )

    draft_index: dict[Tuple[Tuple[str, ...], str], JsonDict] = {}
    for output in transform_outputs:
        for draft in output.get("draft_skills", []):
            clusters_key = tuple(sorted(str(x) for x in draft.get("source_cluster_ids", [])))
            name_key = _normalize_name(str(draft.get("name", "")))
            if not clusters_key or not name_key:
                continue
            key = (clusters_key, name_key)
            if key not in draft_index:
                draft_index[key] = {
                    "name": str(draft.get("name", "")).strip(),
                    "definition": str(draft.get("definition", "")).strip(),
                    "source_cluster_ids": list(clusters_key),
                    "support_count": 0,
                    "inclusion_counter": Counter(),
                    "exclusion_counter": Counter(),
                }
            entry = draft_index[key]
            entry["support_count"] += 1
            for item in draft.get("inclusion_criteria", []):
                txt = str(item).strip()
                if txt:
                    entry["inclusion_counter"][txt] += 1
            for item in draft.get("exclusion_criteria", []):
                txt = str(item).strip()
                if txt:
                    entry["exclusion_counter"][txt] += 1

    draft_skill_candidates: list[JsonDict] = []
    for idx, entry in enumerate(sorted(draft_index.values(), key=lambda x: (-x["support_count"], x["name"])), start=1):
        draft_skill_candidates.append(
            {
                "provisional_skill_id": f"CDS{idx:02d}",
                "name": entry["name"],
                "definition": entry["definition"],
                "source_cluster_ids": entry["source_cluster_ids"],
                "support_count": int(entry["support_count"]),
                "inclusion_criteria": [text for text, _ in entry["inclusion_counter"].most_common(5)],
                "exclusion_criteria": [text for text, _ in entry["exclusion_counter"].most_common(5)],
            }
        )

    stable_groups: set[tuple[str, ...]] = set()
    for decision in decisions_out:
        cid = decision["cluster_id"]
        action = decision["consensus_action"]
        targets = [str(x) for x in decision.get("target_cluster_ids", []) if str(x)]
        if action == "keep":
            stable_groups.add((cid,))
        elif action == "merge" and targets:
            stable_groups.add(tuple(sorted(set([cid, *targets]))))
    recommended_final_k = max(1, len(stable_groups) + len(disputed))

    summary = (
        f"Consensus built from {len(transform_outputs)} transformer outputs across {len(clusters)} scaffold clusters. "
        f"Disputed clusters: {len(disputed)}. Recommended draft final K: {recommended_final_k}."
    )

    consensus = TransformConsensus(
        version="v1",
        recommended_final_k=recommended_final_k,
        consensus_decisions=decisions_out,
        draft_skill_candidates=draft_skill_candidates,
        disputed_clusters=disputed,
        summary=summary,
    )
    return consensus.model_dump()


def transform_consensus_to_prompt_text(consensus: JsonDict) -> str:
    lines: list[str] = []
    lines.append("TRANSFORMATION CONSENSUS LAYER")
    lines.append(f"Recommended draft final K: {consensus.get('recommended_final_k', '?')}")
    lines.append("Use this as a structured intermediate layer between scaffold clusters and the final codebook.")
    for decision in consensus.get("consensus_decisions", []):
        cid = decision.get("cluster_id", "?")
        action = decision.get("consensus_action", "?")
        agreement = decision.get("agreement", "?")
        lines.append(f"- {cid}: {action} ({agreement})")
        names = ", ".join(decision.get("proposed_skill_names", [])[:3])
        if names:
            lines.append(f"  proposed names: {names}")
        targets = ", ".join(decision.get("target_cluster_ids", [])[:4])
        if targets:
            lines.append(f"  targets: {targets}")
    if consensus.get("draft_skill_candidates"):
        lines.append("Consensus draft skill candidates:")
        for draft in consensus.get("draft_skill_candidates", [])[:10]:
            name = draft.get("name", "?")
            support = draft.get("support_count", 0)
            src = ", ".join(draft.get("source_cluster_ids", []))
            lines.append(f"- {name} [support={support}; clusters={src}]")
    return "\n".join(lines)
