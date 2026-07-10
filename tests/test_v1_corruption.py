import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.v1_sensitivity import check_monotonicity, corrupt

MATRIX = [
    [1, 0, 1, 0],
    [0, 1, 0, 1],
    [1, 1, 0, 0],
    [0, 0, 1, 1],
    [1, 0, 0, 1],
]


def _count_diffs(a, b):
    return sum(x != y for ra, rb in zip(a, b) for x, y in zip(ra, rb))


def test_exact_flip_count():
    n_flips = round(0.2 * 20)
    n_flips -= n_flips % 2
    corrupted, _ = corrupt(MATRIX, 0.2, random.Random(1))
    assert _count_diffs(MATRIX, corrupted) == n_flips


def test_density_preserved():
    for seed in range(10):
        corrupted, _ = corrupt(MATRIX, 0.2, random.Random(seed))
        assert sum(map(sum, corrupted)) == sum(map(sum, MATRIX))


def test_no_all_zero_rows_or_cols():
    for seed in range(30):
        corrupted, _ = corrupt(MATRIX, 0.3, random.Random(seed))
        assert all(sum(row) > 0 for row in corrupted)
        n_items, n_skills = len(corrupted), len(corrupted[0])
        assert all(any(corrupted[i][j] for i in range(n_items)) for j in range(n_skills))


def test_seed_reproducibility():
    a, _ = corrupt(MATRIX, 0.2, random.Random(42))
    b, _ = corrupt(MATRIX, 0.2, random.Random(42))
    assert a == b


def test_rate_zero_identity():
    corrupted, n_resamples = corrupt(MATRIX, 0.0, random.Random(1))
    assert corrupted == MATRIX
    assert corrupted is not MATRIX  # must be a copy
    assert n_resamples == 0


def test_monotonicity_check():
    verdicts = check_monotonicity({
        "RMSEA2": [(0.0, 0.03), (0.05, 0.05), (0.10, 0.08)],       # up, monotone
        "ca_test_level": [(0.0, 0.95), (0.05, 0.9), (0.10, 0.92)],  # down, violated
    })
    assert verdicts["RMSEA2"]["monotone"] is True
    assert verdicts["ca_test_level"]["monotone"] is False
