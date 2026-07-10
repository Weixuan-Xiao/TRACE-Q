import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.check_structure import check_structure

ITEMS = ["I1", "I2", "I3", "I4"]
SKILLS = ["S01", "S02", "S03"]


def _violation_rules(result):
    return [v["rule"] for v in result["violations"]]


def test_clean_matrix_no_violations():
    matrix = [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
        [1, 1, 1],
    ]
    result = check_structure(ITEMS, SKILLS, matrix)
    assert result["n_errors"] == 0
    assert result["n_warnings"] == 0
    assert result["density"] == round(6 / 12, 4)
    assert result["item_skill_count_distribution"] == {"1": 3, "3": 1}


def test_all_zero_row():
    matrix = [
        [0, 0, 0],
        [1, 1, 0],
        [1, 0, 1],
        [0, 1, 1],
    ]
    result = check_structure(ITEMS, SKILLS, matrix)
    assert "all_zero_row" in _violation_rules(result)
    assert result["checks"]["all_zero_rows"]["details"] == ["I1"]


def test_all_zero_col():
    matrix = [
        [1, 0, 0],
        [1, 0, 0],
        [0, 0, 1],
        [1, 0, 1],
    ]
    result = check_structure(ITEMS, SKILLS, matrix)
    assert "all_zero_col" in _violation_rules(result)
    assert result["checks"]["all_zero_cols"]["details"] == ["S02"]


def test_duplicate_cols():
    matrix = [
        [1, 1, 0],
        [0, 0, 1],
        [1, 1, 0],
        [1, 1, 1],
    ]
    result = check_structure(ITEMS, SKILLS, matrix)
    assert "duplicate_cols" in _violation_rules(result)
    assert result["checks"]["duplicate_cols"]["details"] == [["S01", "S02"]]


def test_skill_coverage():
    matrix = [
        [1, 0, 1],
        [1, 0, 1],
        [1, 1, 0],
        [1, 0, 1],
    ]
    result = check_structure(ITEMS, SKILLS, matrix, min_items_per_skill=2)
    rules = _violation_rules(result)
    assert "skill_coverage" in rules
    details = result["checks"]["skill_coverage"]["details"]
    assert details == [{"skill": "S02", "n_items": 1}]


def test_single_attribute_warning():
    matrix = [
        [1, 1, 0],
        [1, 0, 1],
        [0, 1, 1],
        [1, 1, 1],
    ]
    result = check_structure(ITEMS, SKILLS, matrix)
    assert result["n_warnings"] == 3
    assert result["checks"]["single_attribute_item"]["details"]["skills_without"] == SKILLS
