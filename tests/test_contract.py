import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.contract import discover_runs, load_run, validate_run


def _make_run(tmp_path, name="run1", q_rows=None, config=None, codebook=None):
    run_dir = tmp_path / name
    run_dir.mkdir()
    if q_rows is None:
        q_rows = [
            "item_id,S01,S02",
            "FS01,1,0",
            "FS02,0,1",
        ]
    (run_dir / "Q.csv").write_text("\n".join(q_rows) + "\n")
    if config is None:
        config = {
            "method": "test_method",
            "dataset": "tatsuoka",
            "k_condition": "fixed_2",
            "k_selected": 2,
            "timestamp": "2026-07-10T00:00:00Z",
        }
    (run_dir / "config.json").write_text(json.dumps(config))
    if codebook is not None:
        (run_dir / "codebook.json").write_text(json.dumps(codebook))
    return run_dir


def test_valid_run_passes(tmp_path):
    run_dir = _make_run(tmp_path)
    assert validate_run(run_dir) == []


def test_valid_run_with_codebook_passes(tmp_path):
    codebook = {"skills": [
        {"skill_id": "S01", "name": "A", "definition": "def a"},
        {"skill_id": "S02", "name": "B", "definition": "def b"},
    ]}
    run_dir = _make_run(tmp_path, codebook=codebook)
    assert validate_run(run_dir) == []


def test_missing_config_field(tmp_path):
    config = {"method": "m", "dataset": "d", "k_selected": 2, "timestamp": "t"}
    run_dir = _make_run(tmp_path, config=config)
    violations = validate_run(run_dir)
    assert any("missing fields" in v and "k_condition" in v for v in violations)


def test_non_binary_cell(tmp_path):
    rows = ["item_id,S01,S02", "FS01,1,2", "FS02,0,1"]
    run_dir = _make_run(tmp_path, q_rows=rows)
    violations = validate_run(run_dir)
    assert any("non-binary" in v for v in violations)


def test_k_selected_mismatch(tmp_path):
    config = {
        "method": "m", "dataset": "d", "k_condition": "auto",
        "k_selected": 3, "timestamp": "t",
    }
    run_dir = _make_run(tmp_path, config=config)
    violations = validate_run(run_dir)
    assert any("k_selected=3" in v for v in violations)


def test_bad_k_condition(tmp_path):
    config = {
        "method": "m", "dataset": "d", "k_condition": "sometimes",
        "k_selected": 2, "timestamp": "t",
    }
    run_dir = _make_run(tmp_path, config=config)
    violations = validate_run(run_dir)
    assert any("k_condition" in v for v in violations)


def test_codebook_skill_mismatch(tmp_path):
    codebook = {"skills": [
        {"skill_id": "S01", "name": "A", "definition": "def a"},
        {"skill_id": "S99", "name": "B", "definition": "def b"},
    ]}
    run_dir = _make_run(tmp_path, codebook=codebook)
    violations = validate_run(run_dir)
    assert any("codebook" in v for v in violations)


def test_missing_q_csv(tmp_path):
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    (run_dir / "config.json").write_text("{}")
    assert "missing Q.csv" in validate_run(run_dir)


def test_load_run_and_discover(tmp_path):
    _make_run(tmp_path, name="a_run1")
    _make_run(tmp_path, name="a_run2")
    (tmp_path / "not_a_run").mkdir()
    runs = discover_runs(tmp_path)
    assert [r.name for r in runs] == ["a_run1", "a_run2"]
    loaded = load_run(runs[0])
    assert loaded["items"] == ["FS01", "FS02"]
    assert loaded["skills"] == ["S01", "S02"]
    assert loaded["matrix"] == [[1, 0], [0, 1]]
    assert loaded["config"]["method"] == "test_method"
    assert loaded["codebook"] is None
