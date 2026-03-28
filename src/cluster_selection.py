from __future__ import annotations

from typing import Any, Dict, List, Sequence

JsonDict = Dict[str, Any]


def summarize_candidate_table(candidates: Sequence[JsonDict]) -> List[JsonDict]:
    rows: List[JsonDict] = []
    for candidate in candidates:
        metrics = candidate.get("metrics", {})
        rows.append(
            {
                "k": candidate.get("k"),
                "overall": metrics.get("overall"),
                "stability": metrics.get("stability"),
                "silhouette": metrics.get("silhouette"),
                "interpretability": metrics.get("interpretability"),
                "balance": metrics.get("balance"),
                "cluster_sizes": candidate.get("cluster_sizes", []),
            }
        )
    return rows


def select_candidate_by_k(candidates: Sequence[JsonDict], k: int) -> JsonDict | None:
    for candidate in candidates:
        if int(candidate.get("k", -1)) == int(k):
            return dict(candidate)
    return None
