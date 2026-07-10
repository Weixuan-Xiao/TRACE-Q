import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.expert_agreement import aligned_agreement

Q_EXPERT = [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
    [1, 1, 0],
]


def _shuffle_cols(matrix, perm):
    return [[row[p] for p in perm] for row in matrix]


def test_identical_equal_k():
    result = aligned_agreement(Q_EXPERT, Q_EXPERT)
    assert result["cell_agreement"] == 1.0
    assert result["precision_1cells"] == 1.0
    assert result["recall_1cells"] == 1.0
    assert result["n_unmatched_expert_skills"] == 0


def test_column_shuffle_recovered():
    shuffled = _shuffle_cols(Q_EXPERT, [2, 0, 1])
    result = aligned_agreement(shuffled, Q_EXPERT)
    assert result["cell_agreement"] == 1.0
    # column 0 of shuffled is expert column 2, etc.
    assert result["assignment"] == [[0, 2], [1, 0], [2, 1]]


def test_smaller_method_k():
    # method has only expert columns 0 and 2
    q_method = [[row[0], row[2]] for row in Q_EXPERT]
    result = aligned_agreement(q_method, Q_EXPERT)
    assert result["k_method"] == 2
    assert result["k_expert"] == 3
    assert result["cell_agreement"] == 1.0
    assert result["n_matched_skills"] == 2
    assert result["n_unmatched_expert_skills"] == 1
    assert result["n_unmatched_method_skills"] == 0


def test_larger_method_k():
    q_method = [[row[0], row[1], row[2], 1 - row[0]] for row in Q_EXPERT]
    result = aligned_agreement(q_method, Q_EXPERT)
    assert result["k_method"] == 4
    assert result["n_matched_skills"] == 3
    assert result["cell_agreement"] == 1.0
    assert result["n_unmatched_method_skills"] == 1


def test_matched_pair_names():
    shuffled = _shuffle_cols(Q_EXPERT, [1, 0, 2])
    result = aligned_agreement(shuffled, Q_EXPERT,
                               method_skills=["M1", "M2", "M3"],
                               expert_skills=["A1", "A2", "A3"])
    assert ["M1", "A2"] in result["matched_pairs"]
    assert ["M2", "A1"] in result["matched_pairs"]
