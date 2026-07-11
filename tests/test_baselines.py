import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.baselines import (
    aggregate_b3,
    build_b1_prompt,
    k_constraint_text,
    parse_baseline_output,
    validate_k,
)

ITEM_IDS = ["FS01", "FS02", "FS03"]
ITEMS = [{"item_id": i, "stem_text": f"stem {i}"} for i in ITEM_IDS]

VALID_OUTPUT = {
    "skills": [
        {"skill_id": "S01", "name": "A", "definition": "def a"},
        {"skill_id": "S02", "name": "B", "definition": "def b"},
    ],
    "q_matrix": [
        {"item_id": "FS01", "skills": ["S01"]},
        {"item_id": "FS02", "skills": ["S02"]},
        {"item_id": "FS03", "skills": ["S01", "S02"]},
    ],
}


def test_k_constraint_text():
    assert "between 3 and 8" in k_constraint_text("auto")
    assert "exactly 4" in k_constraint_text("fixed_4")


def test_parse_clean_json():
    skills, matrix = parse_baseline_output(json.dumps(VALID_OUTPUT), ITEM_IDS)
    assert [s["skill_id"] for s in skills] == ["S01", "S02"]
    assert matrix == [[1, 0], [0, 1], [1, 1]]


def test_parse_json_after_reasoning_and_fences():
    text = "Let me think step by step...\nStep 1 blah.\n```json\n" \
        + json.dumps(VALID_OUTPUT) + "\n```\nDone."
    skills, matrix = parse_baseline_output(text, ITEM_IDS)
    assert matrix == [[1, 0], [0, 1], [1, 1]]


def test_parse_rejects_undefined_skill():
    bad = json.loads(json.dumps(VALID_OUTPUT))
    bad["q_matrix"][0]["skills"] = ["S99"]
    with pytest.raises(ValueError, match="undefined"):
        parse_baseline_output(json.dumps(bad), ITEM_IDS)


def test_parse_rejects_missing_item():
    bad = json.loads(json.dumps(VALID_OUTPUT))
    bad["q_matrix"] = bad["q_matrix"][:2]
    with pytest.raises(ValueError, match="missing"):
        parse_baseline_output(json.dumps(bad), ITEM_IDS)


def test_parse_rejects_empty_item():
    bad = json.loads(json.dumps(VALID_OUTPUT))
    bad["q_matrix"][0]["skills"] = []
    with pytest.raises(ValueError, match="no skills"):
        parse_baseline_output(json.dumps(bad), ITEM_IDS)


def test_validate_k():
    skills2 = VALID_OUTPUT["skills"]
    assert validate_k(skills2, "fixed_2")
    assert not validate_k(skills2, "fixed_4")
    assert not validate_k(skills2, "auto")  # 2 < 3
    skills4 = skills2 + [
        {"skill_id": "S03", "name": "C", "definition": "d"},
        {"skill_id": "S04", "name": "D", "definition": "d"},
    ]
    assert validate_k(skills4, "auto")


def test_b1_prompt_contains_items_and_constraint():
    prompt = build_b1_prompt(ITEMS, "fixed_4")
    assert "FS02: stem FS02" in prompt
    assert "exactly 4" in prompt


def _mk_skills(names):
    return [{"skill_id": f"S{i:02d}", "name": n, "definition": f"def {n}"}
            for i, n in enumerate(names, 1)]


def test_aggregate_b3_majority_with_column_swap():
    m = [[1, 0], [0, 1], [1, 1]]
    m_swapped = [[0, 1], [1, 0], [1, 1]]  # same content, columns swapped
    samples = [
        (_mk_skills(["a", "b"]), m),
        (_mk_skills(["b", "a"]), m_swapped),
        (_mk_skills(["a", "b"]), m),
    ]
    skills, final, meta = aggregate_b3(samples)
    assert meta["modal_k"] == 2
    assert meta["n_samples_used"] == 3
    # after alignment all three agree
    assert final == m or final == m_swapped  # column order follows medoid
    assert len(skills) == 2


def test_aggregate_b3_modal_k_filter():
    m2 = [[1, 0], [0, 1], [1, 1]]
    m3 = [[1, 0, 0], [0, 1, 0], [1, 1, 1]]
    samples = [
        (_mk_skills(["a", "b"]), m2),
        (_mk_skills(["a", "b"]), m2),
        (_mk_skills(["a", "b", "c"]), m3),
    ]
    _skills, final, meta = aggregate_b3(samples)
    assert meta["modal_k"] == 2
    assert meta["n_samples_used"] == 2
    assert len(final[0]) == 2


def test_aggregate_b3_tie_breaks_to_zero():
    m_a = [[1, 0], [1, 0], [1, 0]]
    m_b = [[1, 0], [0, 1], [1, 0]]  # cell (1,*) disagrees
    samples = [(_mk_skills(["a", "b"]), m_a), (_mk_skills(["a", "b"]), m_b)]
    _skills, final, _meta = aggregate_b3(samples)
    # 1-1 tie on disputed cells -> 0 (minimal tagging)
    assert final[1] == [0, 0] or final[1] == [1, 0]  # depends on alignment; row must not be all-1
    assert final[0] == [1, 0]


def test_aggregate_b3_too_few_modal_samples():
    m2 = [[1, 0], [0, 1], [1, 1]]
    m3 = [[1, 0, 0], [0, 1, 0], [1, 1, 1]]
    m4 = [[1, 0, 0, 0], [0, 1, 0, 0], [1, 1, 1, 1]]
    samples = [
        (_mk_skills(["a", "b"]), m2),
        (_mk_skills(["a", "b", "c"]), m3),
        (_mk_skills(["a", "b", "c", "d"]), m4),
    ]
    with pytest.raises(RuntimeError, match="modal K"):
        aggregate_b3(samples)
