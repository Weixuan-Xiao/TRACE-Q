from __future__ import annotations

import math
import random
from typing import Any, Dict, Iterable, List, Sequence

from src.embedding_client import EmbeddingClient
from src.structure_discovery import (
    agglomerative_partition_from_distance,
    balance_score,
    card_to_document,
    cluster_top_terms,
    evaluate_partition,
    labels_to_clusters,
    pairwise_agreement_score,
)

JsonDict = Dict[str, Any]


def _normalize(vec: Sequence[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_reasoning_cards(cards: Sequence[JsonDict], embedding_model: str | None = None) -> List[List[float]]:
    texts = [card_to_document(card) for card in cards]
    client = EmbeddingClient(model=embedding_model)
    embeddings = client.embed_texts(texts)
    return [_normalize(vec) for vec in embeddings]


def build_distance_matrix_from_embeddings(embeddings: Sequence[Sequence[float]]) -> List[List[float]]:
    n = len(embeddings)
    dist = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        vec_i = embeddings[i]
        for j in range(i + 1, n):
            dot = sum(a * b for a, b in zip(vec_i, embeddings[j]))
            value = max(0.0, min(2.0, 1.0 - dot))
            dist[i][j] = value
            dist[j][i] = value
    return dist


def _simple_top_terms(cards: Sequence[JsonDict], members: Sequence[int], *, top_n: int = 8) -> list[str]:
    from collections import Counter
    from src.structure_discovery import _tokenize  # reuse tokenizer

    combined = Counter()
    for idx in members:
        combined.update(_tokenize(card_to_document(cards[idx])))
    return [tok for tok, _ in combined.most_common(top_n)]


def _subset_distance_matrix(dist: Sequence[Sequence[float]], subset: Sequence[int]) -> list[list[float]]:
    return [[dist[i][j] for j in subset] for i in subset]


def stability_score_from_embeddings(
    labels: Sequence[int],
    dist: Sequence[Sequence[float]],
    *,
    n_trials: int = 4,
    sample_ratio: float = 0.85,
    seed: int = 17,
) -> float:
    n = len(labels)
    grouped = labels_to_clusters(labels)
    k = len(grouped)
    if n < 4 or k <= 1:
        return 1.0

    rng = random.Random(seed)
    scores: list[float] = []
    sample_size = max(k + 1, int(round(n * sample_ratio)))
    sample_size = min(sample_size, n)
    for _ in range(n_trials):
        subset = sorted(rng.sample(range(n), sample_size))
        sub_dist = _subset_distance_matrix(dist, subset)
        partitions = agglomerative_partition_from_distance(sub_dist, [min(k, sample_size)])
        subset_labels = partitions.get(min(k, sample_size))
        if subset_labels is None:
            continue
        scores.append(pairwise_agreement_score(labels, subset, subset_labels))
    return sum(scores) / len(scores) if scores else 0.0


def search_candidate_partitions_embed(
    cards: Sequence[JsonDict],
    *,
    embedding_model: str | None = None,
    min_k: int = 3,
    max_k: int = 8,
) -> JsonDict:
    n = len(cards)
    if n == 0:
        return {"candidates": [], "selected_k": None, "selected_labels": []}

    max_allowed = max(1, min(max_k, n))
    min_allowed = max(1, min(min_k, max_allowed))
    if min_allowed > max_allowed:
        min_allowed = max_allowed

    embeddings = embed_reasoning_cards(cards, embedding_model=embedding_model)
    dist = build_distance_matrix_from_embeddings(embeddings)
    k_values = list(range(min_allowed, max_allowed + 1))
    partitions = agglomerative_partition_from_distance(dist, k_values)

    candidates: list[JsonDict] = []
    for k in sorted(partitions):
        labels = partitions[k]
        grouped = labels_to_clusters(labels)
        metrics = evaluate_partition(labels, dist, raw_counts=[{} for _ in cards])
        metrics["stability"] = round(stability_score_from_embeddings(labels, dist), 4)
        metrics["overall"] = round(
            (0.45 * metrics["stability"]) + (0.35 * metrics["silhouette"]) + (0.10 * metrics["interpretability"]) + (0.10 * metrics["balance"]),
            4,
        )
        candidate = {
            "k": k,
            "metrics": metrics,
            "cluster_sizes": sorted((len(members) for members in grouped.values()), reverse=True),
            "top_terms": {
                str(label): _simple_top_terms(cards, members)
                for label, members in grouped.items()
            },
            "labels": labels,
        }
        candidates.append(candidate)

    candidates.sort(key=lambda c: (-c["metrics"]["overall"], c["k"]))
    selected = candidates[0]
    return {
        "candidates": candidates,
        "selected_k": selected["k"],
        "selected_labels": selected["labels"],
        "distance_matrix": dist,
        "embeddings": embeddings,
    }
