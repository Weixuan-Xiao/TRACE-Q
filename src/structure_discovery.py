from __future__ import annotations

import math
import random
import re
from collections import Counter, defaultdict
from statistics import pstdev
from typing import Any, Dict, Iterable, List, Sequence

JsonDict = Dict[str, Any]

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "if", "in", "into",
    "is", "it", "of", "on", "or", "so", "such", "that", "the", "their", "then", "there",
    "these", "this", "to", "we", "when", "with", "you", "your", "find", "let", "show",
    "using", "use", "compute", "suppose", "given", "value", "values", "expression", "answer",
}


def _tokenize(text: str) -> list[str]:
    return [
        tok for tok in re.findall(r"[A-Za-z][A-Za-z_\-']+", (text or "").lower())
        if tok not in _STOPWORDS and len(tok) > 2
    ]


def card_to_document(card: JsonDict) -> str:
    stem = str(card.get("stem_text", ""))
    summary = str(card.get("solution_summary", ""))
    steps = " ".join(str(x) for x in card.get("step_texts", []))
    # Upweight steps (they carry the most reasoning signal).
    return " ".join([stem, summary, steps, steps])


def build_tfidf_vectors(cards: Sequence[JsonDict]) -> tuple[list[dict[str, float]], list[Counter[str]]]:
    docs_tokens: list[list[str]] = []
    raw_counts: list[Counter[str]] = []
    df: Counter[str] = Counter()

    for card in cards:
        tokens = _tokenize(card_to_document(card))
        if not tokens:
            tokens = ["misc"]
        docs_tokens.append(tokens)
        counts = Counter(tokens)
        raw_counts.append(counts)
        for token in counts:
            df[token] += 1

    n_docs = max(len(cards), 1)
    idf = {tok: math.log((1 + n_docs) / (1 + freq)) + 1.0 for tok, freq in df.items()}

    vectors: list[dict[str, float]] = []
    for counts in raw_counts:
        total = sum(counts.values()) or 1
        vec = {tok: (cnt / total) * idf[tok] for tok, cnt in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({tok: v / norm for tok, v in vec.items()})

    return vectors, raw_counts


def _cosine_from_sparse(v1: dict[str, float], v2: dict[str, float]) -> float:
    if len(v1) > len(v2):
        v1, v2 = v2, v1
    return sum(value * v2.get(tok, 0.0) for tok, value in v1.items())


def build_distance_matrix(vectors: Sequence[dict[str, float]]) -> list[list[float]]:
    n = len(vectors)
    dist = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            similarity = _cosine_from_sparse(vectors[i], vectors[j])
            value = max(0.0, min(2.0, 1.0 - similarity))
            dist[i][j] = value
            dist[j][i] = value
    return dist


def _average_linkage_distance(cluster_a: list[int], cluster_b: list[int], dist: Sequence[Sequence[float]]) -> float:
    total = 0.0
    count = 0
    for i in cluster_a:
        for j in cluster_b:
            total += dist[i][j]
            count += 1
    return total / max(count, 1)


def agglomerative_partition_from_distance(
    dist: Sequence[Sequence[float]],
    k_values: Iterable[int],
) -> dict[int, list[int]]:
    n = len(dist)
    if n == 0:
        return {}

    wanted = {k for k in k_values if 1 <= k <= n}
    if not wanted:
        return {}

    clusters: dict[int, list[int]] = {i: [i] for i in range(n)}
    next_cluster_id = n
    partitions: dict[int, list[int]] = {}

    def snapshot(current_clusters: dict[int, list[int]]) -> list[int]:
        labels = [-1] * n
        ordered = sorted(current_clusters.values(), key=lambda members: (members[0], len(members)))
        for label, members in enumerate(ordered):
            for idx in members:
                labels[idx] = label
        return labels

    while clusters:
        current_k = len(clusters)
        if current_k in wanted and current_k not in partitions:
            partitions[current_k] = snapshot(clusters)
        if current_k == 1:
            break

        cluster_ids = list(clusters.keys())
        best_pair: tuple[int, int] | None = None
        best_distance = float("inf")
        for i, cid_a in enumerate(cluster_ids):
            for cid_b in cluster_ids[i + 1 :]:
                value = _average_linkage_distance(clusters[cid_a], clusters[cid_b], dist)
                if value < best_distance:
                    best_distance = value
                    best_pair = (cid_a, cid_b)

        if best_pair is None:
            break

        cid_a, cid_b = best_pair
        merged = sorted(clusters.pop(cid_a) + clusters.pop(cid_b))
        clusters[next_cluster_id] = merged
        next_cluster_id += 1

    return partitions


def labels_to_clusters(labels: Sequence[int]) -> dict[int, list[int]]:
    grouped: dict[int, list[int]] = defaultdict(list)
    for idx, label in enumerate(labels):
        grouped[int(label)].append(idx)
    return dict(sorted(grouped.items(), key=lambda pair: pair[0]))


def silhouette_score_from_distance(labels: Sequence[int], dist: Sequence[Sequence[float]]) -> float:
    grouped = labels_to_clusters(labels)
    if len(grouped) <= 1:
        return 0.0

    score_total = 0.0
    n = len(labels)
    for idx in range(n):
        own = grouped[labels[idx]]
        if len(own) <= 1:
            continue
        a = sum(dist[idx][j] for j in own if j != idx) / max(len(own) - 1, 1)
        b = min(
            sum(dist[idx][j] for j in members) / max(len(members), 1)
            for label, members in grouped.items()
            if label != labels[idx]
        )
        denom = max(a, b, 1e-9)
        score_total += (b - a) / denom
    return score_total / max(n, 1)


def balance_score(labels: Sequence[int]) -> float:
    grouped = labels_to_clusters(labels)
    sizes = [len(members) for members in grouped.values()]
    if not sizes:
        return 0.0
    mean = sum(sizes) / len(sizes)
    if mean <= 0:
        return 0.0
    cv = pstdev(sizes) / mean if len(sizes) > 1 else 0.0
    return 1.0 / (1.0 + cv)


def cluster_top_terms(
    cluster_members: Sequence[int],
    raw_counts: Sequence[Counter[str]],
    *,
    top_n: int = 8,
) -> list[str]:
    combined = Counter()
    for idx in cluster_members:
        combined.update(raw_counts[idx])
    return [tok for tok, _ in combined.most_common(top_n)]


def cluster_distinguishing_terms(
    cluster_members: Sequence[int],
    all_raw_counts: Sequence[Counter[str]],
    all_members: Sequence[Sequence[int]],
    *,
    top_n: int = 5,
) -> list[str]:
    """Extract terms that distinguish this cluster from all other clusters.

    Uses a TF-IDF-like score: TF (frequency within cluster) weighted by
    inverse cluster frequency (how many other clusters also use this term).
    """
    import math

    # Term frequency within this cluster
    cluster_tf: Counter[str] = Counter()
    for idx in cluster_members:
        cluster_tf.update(all_raw_counts[idx])
    total_tf = sum(cluster_tf.values()) or 1

    # Cluster frequency: in how many clusters does each term appear?
    n_clusters = len(all_members)
    cluster_freq: Counter[str] = Counter()
    for members in all_members:
        terms_in_cluster: set[str] = set()
        for idx in members:
            terms_in_cluster.update(all_raw_counts[idx].keys())
        for term in terms_in_cluster:
            cluster_freq[term] += 1

    # Score: tf * log(n_clusters / cf)
    scored: list[tuple[str, float]] = []
    for term, tf in cluster_tf.items():
        cf = cluster_freq.get(term, 1)
        idf = math.log((n_clusters + 1) / (cf + 1)) + 1.0
        scored.append((term, (tf / total_tf) * idf))

    scored.sort(key=lambda x: -x[1])
    return [term for term, _ in scored[:top_n]]


def interpretability_score(labels: Sequence[int], raw_counts: Sequence[Counter[str]]) -> float:
    grouped = labels_to_clusters(labels)
    if not grouped:
        return 0.0
    scores: list[float] = []
    for members in grouped.values():
        combined = Counter()
        for idx in members:
            combined.update(raw_counts[idx])
        total = sum(combined.values()) or 1
        top3 = sum(count for _, count in combined.most_common(3))
        scores.append(top3 / total)
    return sum(scores) / len(scores)


def _subset_distance_matrix(dist: Sequence[Sequence[float]], subset: Sequence[int]) -> list[list[float]]:
    return [[dist[i][j] for j in subset] for i in subset]


def pairwise_agreement_score(full_labels: Sequence[int], subset_indices: Sequence[int], subset_labels: Sequence[int]) -> float:
    agreements = 0
    total = 0
    for i, global_i in enumerate(subset_indices):
        for j, global_j in enumerate(subset_indices[i + 1 :], start=i + 1):
            same_full = full_labels[global_i] == full_labels[global_j]
            same_subset = subset_labels[i] == subset_labels[j]
            agreements += int(same_full == same_subset)
            total += 1
    return agreements / total if total else 1.0


def stability_score(
    labels: Sequence[int],
    dist: Sequence[Sequence[float]],
    *,
    n_trials: int = 4,
    sample_ratio: float = 0.85,
    seed: int = 13,
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


def evaluate_partition(labels: Sequence[int], dist: Sequence[Sequence[float]], raw_counts: Sequence[Counter[str]]) -> JsonDict:
    silhouette = silhouette_score_from_distance(labels, dist)
    balance = balance_score(labels)
    interpretability = interpretability_score(labels, raw_counts)
    stability = stability_score(labels, dist)
    overall = (0.40 * stability) + (0.30 * silhouette) + (0.20 * interpretability) + (0.10 * balance)
    return {
        "silhouette": round(silhouette, 4),
        "balance": round(balance, 4),
        "interpretability": round(interpretability, 4),
        "stability": round(stability, 4),
        "overall": round(overall, 4),
    }


def search_candidate_partitions(
    cards: Sequence[JsonDict],
    *,
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

    vectors, raw_counts = build_tfidf_vectors(cards)
    dist = build_distance_matrix(vectors)
    k_values = list(range(min_allowed, max_allowed + 1))
    partitions = agglomerative_partition_from_distance(dist, k_values)

    candidates: list[JsonDict] = []
    for k in sorted(partitions):
        labels = partitions[k]
        grouped = labels_to_clusters(labels)
        candidate = {
            "k": k,
            "metrics": evaluate_partition(labels, dist, raw_counts),
            "cluster_sizes": sorted((len(members) for members in grouped.values()), reverse=True),
            "top_terms": {
                str(label): cluster_top_terms(members, raw_counts)
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
        "raw_counts": raw_counts,
    }
