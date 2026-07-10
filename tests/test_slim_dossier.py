"""Tests for slim_dossier_for_llm in src/agent_utils.py."""
import sys
from pathlib import Path

# Ensure project root is on sys.path so `src.*` imports resolve.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent_utils import slim_dossier_for_llm


FULL_DOSSIER = {
    "item_id": "FS01",
    "item": {
        "item_id": "FS01",
        "stem_text": "What is 2+3?",
        "answer_rules": "integer only",
    },
    "solver": {
        "answer_canonical": ["5"],
        "solution_steps": [
            {"step_id": "Step1", "text": "Add 2 and 3"},
            {"step_id": "Step2", "text": "Result is 5"},
        ],
    },
    "verifier": {"ok": True, "issues": [], "corrected": False},
    "created_at": "2025-01-01T00:00:00Z",
    "stage": "verified",
}


def test_keeps_item_id():
    slim = slim_dossier_for_llm(FULL_DOSSIER)
    assert slim["item_id"] == "FS01"


def test_keeps_stem_text():
    slim = slim_dossier_for_llm(FULL_DOSSIER)
    assert slim["item"]["stem_text"] == "What is 2+3?"
    assert slim["item"]["item_id"] == "FS01"


def test_keeps_solution_steps():
    slim = slim_dossier_for_llm(FULL_DOSSIER)
    steps = slim["solver"]["solution_steps"]
    assert len(steps) == 2
    assert steps[0] == {"step_id": "Step1", "text": "Add 2 and 3"}
    assert steps[1] == {"step_id": "Step2", "text": "Result is 5"}


def test_drops_answer_rules():
    slim = slim_dossier_for_llm(FULL_DOSSIER)
    assert "answer_rules" not in slim.get("item", {})


def test_drops_answer_canonical():
    slim = slim_dossier_for_llm(FULL_DOSSIER)
    assert "answer_canonical" not in slim.get("solver", {})


def test_drops_verifier():
    slim = slim_dossier_for_llm(FULL_DOSSIER)
    assert "verifier" not in slim


def test_drops_metadata():
    slim = slim_dossier_for_llm(FULL_DOSSIER)
    assert "created_at" not in slim
    assert "stage" not in slim


def test_extract_step_ids_compatible():
    """Ensure slim dossier preserves the path used by _extract_step_ids()."""
    slim = slim_dossier_for_llm(FULL_DOSSIER)
    steps = slim.get("solver", {}).get("solution_steps", [])
    ids = {str(s.get("step_id")).strip() for s in steps if str(s.get("step_id", "")).strip()}
    assert ids == {"Step1", "Step2"}


def test_empty_dossier():
    slim = slim_dossier_for_llm({})
    assert slim["item_id"] == ""
    assert slim["item"]["stem_text"] == ""
    assert slim["solver"]["solution_steps"] == []


def test_missing_solver():
    dossier = {"item_id": "X", "item": {"item_id": "X", "stem_text": "hello"}}
    slim = slim_dossier_for_llm(dossier)
    assert slim["solver"]["solution_steps"] == []


def test_malformed_steps_skipped():
    dossier = {
        "item_id": "X",
        "item": {"item_id": "X", "stem_text": "q"},
        "solver": {"solution_steps": ["not a dict", {"step_id": "S1", "text": "ok"}]},
    }
    slim = slim_dossier_for_llm(dossier)
    assert len(slim["solver"]["solution_steps"]) == 1
    assert slim["solver"]["solution_steps"][0]["step_id"] == "S1"
