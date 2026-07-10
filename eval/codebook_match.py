"""Codebook semantic matching across runs (stability layer 2).

Embeds each skill as "{name}: {definition}", then for each run pair finds the
skill matching that maximizes total cosine similarity and reports the mean
matched similarity.
"""
import hashlib
import json
import math
from itertools import permutations
from pathlib import Path


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def skill_texts(codebook):
    """One text per skill: '{name}: {definition}'."""
    return [f"{s.get('name', '')}: {s.get('definition', '')}" for s in codebook["skills"]]


def embed_texts_cached(texts, embed_fn, cache_path):
    """Embed texts with a sha1-keyed JSON cache. embed_fn(list[str]) -> list[list[float]]."""
    cache_path = Path(cache_path)
    cache = {}
    if cache_path.exists():
        with open(cache_path) as f:
            cache = json.load(f)

    keys = [hashlib.sha1(t.encode()).hexdigest() for t in texts]
    missing = [(i, t) for i, (k, t) in enumerate(zip(keys, texts)) if k not in cache]
    if missing:
        new_vecs = embed_fn([t for _, t in missing])
        for (i, _t), vec in zip(missing, new_vecs):
            cache[keys[i]] = vec
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(cache, f)
    return [cache[k] for k in keys]


def match_score(vecs_a, vecs_b):
    """Best matching between two skill embedding sets.

    Equal K: brute-force permutation maximizing total similarity.
    Unequal K: greedy best-first matching over min(K) pairs.
    Returns {mean_matched_similarity, pairs: [(idx_a, idx_b, sim)]}.
    """
    sim = [[_cosine(a, b) for b in vecs_b] for a in vecs_a]
    n_a, n_b = len(vecs_a), len(vecs_b)

    if n_a == n_b:
        best_total, best_perm = -1.0, None
        for perm in permutations(range(n_b)):
            total = sum(sim[i][perm[i]] for i in range(n_a))
            if total > best_total:
                best_total, best_perm = total, perm
        pairs = [(i, best_perm[i], sim[i][best_perm[i]]) for i in range(n_a)]
    else:
        candidates = sorted(
            ((sim[i][j], i, j) for i in range(n_a) for j in range(n_b)),
            reverse=True,
        )
        used_a, used_b, pairs = set(), set(), []
        for s, i, j in candidates:
            if i in used_a or j in used_b:
                continue
            pairs.append((i, j, s))
            used_a.add(i)
            used_b.add(j)
            if len(pairs) == min(n_a, n_b):
                break

    mean_sim = sum(p[2] for p in pairs) / len(pairs) if pairs else 0.0
    return {"mean_matched_similarity": mean_sim, "pairs": pairs}


def codebook_stability(codebooks, embed_fn, cache_path):
    """Pairwise semantic match over runs' codebooks.

    codebooks: list of (run_id, codebook_dict).
    Returns aggregate {mean, min, sd, n_pairs, pairs: [{a, b, mean_matched_similarity}]}.
    """
    embedded = []
    for run_id, cb in codebooks:
        texts = skill_texts(cb)
        vecs = embed_texts_cached(texts, embed_fn, cache_path)
        embedded.append((run_id, vecs))

    pair_results = []
    for x in range(len(embedded) - 1):
        for y in range(x + 1, len(embedded)):
            score = match_score(embedded[x][1], embedded[y][1])
            pair_results.append({
                "a": embedded[x][0],
                "b": embedded[y][0],
                "mean_matched_similarity": round(score["mean_matched_similarity"], 4),
            })

    if not pair_results:
        return {"error": "need >= 2 codebooks", "n_pairs": 0}

    sims = [p["mean_matched_similarity"] for p in pair_results]
    mean = sum(sims) / len(sims)
    sd = math.sqrt(sum((s - mean) ** 2 for s in sims) / (len(sims) - 1)) if len(sims) > 1 else 0.0
    return {
        "mean": round(mean, 4),
        "min": round(min(sims), 4),
        "sd": round(sd, 4),
        "n_pairs": len(pair_results),
        "pairs": pair_results,
    }
