import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.codebook_match import (
    codebook_stability,
    embed_texts_cached,
    match_score,
    skill_texts,
)

# Fake embedding space: orthogonal unit vectors per concept keyword.
_CONCEPTS = {"convert": [1, 0, 0], "denominator": [0, 1, 0], "simplify": [0, 0, 1]}


def _fake_embed(texts):
    vecs = []
    for t in texts:
        for concept, vec in _CONCEPTS.items():
            if concept in t.lower():
                vecs.append(list(vec))
                break
        else:
            vecs.append([0.5, 0.5, 0.5])
    return vecs


def _codebook(names):
    return {"skills": [
        {"skill_id": f"S{i:02d}", "name": n, "definition": f"about {n}"}
        for i, n in enumerate(names, 1)
    ]}


def test_skill_texts():
    cb = _codebook(["Convert", "Denominator"])
    assert skill_texts(cb) == ["Convert: about Convert", "Denominator: about Denominator"]


def test_match_score_permuted_identical():
    a = _fake_embed(["convert x", "denominator y", "simplify z"])
    b = _fake_embed(["simplify z", "convert x", "denominator y"])
    score = match_score(a, b)
    assert round(score["mean_matched_similarity"], 6) == 1.0


def test_match_score_unequal_k_greedy():
    a = _fake_embed(["convert x", "denominator y"])
    b = _fake_embed(["denominator y", "simplify z", "convert x"])
    score = match_score(a, b)
    assert len(score["pairs"]) == 2
    assert round(score["mean_matched_similarity"], 6) == 1.0


def test_embed_cache_roundtrip(tmp_path):
    calls = []

    def counting_embed(texts):
        calls.append(len(texts))
        return _fake_embed(texts)

    cache = tmp_path / "emb.json"
    v1 = embed_texts_cached(["convert a", "simplify b"], counting_embed, cache)
    v2 = embed_texts_cached(["convert a", "simplify b"], counting_embed, cache)
    assert v1 == v2
    assert calls == [2]  # second call fully served from cache


def test_codebook_stability(tmp_path):
    cb1 = _codebook(["Convert", "Denominator", "Simplify"])
    cb2 = _codebook(["Simplify", "Convert", "Denominator"])  # same concepts, reordered
    result = codebook_stability(
        [("run1", cb1), ("run2", cb2)], _fake_embed, tmp_path / "emb.json"
    )
    assert result["n_pairs"] == 1
    assert result["mean"] == 1.0
    assert result["sd"] == 0.0
