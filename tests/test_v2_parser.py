import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.v2_contamination import parse_q_csv


def test_clean_csv():
    text = "item,A1,A2\nFS01,1,0\nFS02,0,1\nFS03,1,1"
    assert parse_q_csv(text, 3, 2) == [[1, 0], [0, 1], [1, 1]]


def test_code_fences_and_prose():
    text = "Here is the Q-matrix:\n```csv\nitem,A1,A2\n1,1,0\n2,0,1\n```\nHope this helps!"
    assert parse_q_csv(text, 2, 2) == [[1, 0], [0, 1]]


def test_no_item_column():
    text = "1,0\n0,1\n1,1"
    assert parse_q_csv(text, 3, 2) == [[1, 0], [0, 1], [1, 1]]


def test_wrong_row_count_returns_none():
    text = "item,A1,A2\n1,1,0\n2,0,1"
    assert parse_q_csv(text, 5, 2) is None


def test_refusal_returns_none():
    text = "I'm sorry, I cannot reproduce that table from memory."
    assert parse_q_csv(text, 20, 8) is None
