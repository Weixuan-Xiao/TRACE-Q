import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluate_stability import (
    align_matrices,
    compute_stability_from_matrices,
    fleiss_kappa,
    item_perfect_rate,
)

M_A = [
    [1, 0],
    [0, 1],
    [1, 1],
]
M_A_SWAPPED = [
    [0, 1],
    [1, 0],
    [1, 1],
]
M_B = [
    [1, 0],
    [0, 1],
    [0, 1],
]


def test_item_perfect_rate_identical_runs():
    assert item_perfect_rate([M_A, M_A, M_A]) == 1.0


def test_item_perfect_rate_partial():
    # rows 0 and 1 identical across runs, row 2 differs
    assert item_perfect_rate([M_A, M_B]) == 2 / 3


def test_fleiss_kappa_perfect_agreement():
    assert fleiss_kappa([M_A, M_A, M_A], 3) == 1.0


def test_align_recovers_column_swap():
    aligned, _ref_idx, perms = align_matrices([M_A, M_A_SWAPPED])
    assert aligned[0] == aligned[1]
    assert sorted(perms) == [(0, 1), (1, 0)]


def test_compute_stability_from_matrices():
    result = compute_stability_from_matrices([M_A, M_A_SWAPPED])
    assert result["n_runs"] == 2
    assert result["item_perfect_rate"] == round(1 / 3, 4)  # only row 2 identical pre-alignment
    assert result["element_wise_agreement"] < 1.0
    assert result["aligned"]["element_wise_agreement"] == 1.0
    assert result["aligned"]["item_perfect_rate"] == 1.0
    assert result["aligned"]["n_unique_qmatrices"] == 1


def test_too_few_runs():
    result = compute_stability_from_matrices([M_A])
    assert "error" in result
