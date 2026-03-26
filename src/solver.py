"""Solver Agent: two-pass architecture (free-text reasoning + Python parser).

Pass 1 — LLM produces a plain-text step-by-step solution with the format:
    Step1: ...
    Step2: ...
    Answer: <final answer>

Pass 2 — A deterministic Python regex parser converts the text into the JSON
schema expected by downstream agents (``SolverOutput``).

This eliminates format-reasoning interference: the LLM focuses entirely on
math, and the parser guarantees structural consistency.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from schemas.solver_output import SolverOutput
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]

_STEP_RE = re.compile(r"^Step\s*(\d+)\s*:\s*(.+)", re.IGNORECASE)
_ANSWER_RE = re.compile(r"^Answer\s*:\s*(.+)", re.IGNORECASE)
_FINAL_ANSWER_RE = re.compile(r"Final answer:\s*(.+?)\s*$")


def _is_internally_consistent(solver_out: JsonDict) -> bool:
    """Check that last step's 'Final answer: X' matches answer_canonical[0].

    Kept for backward compatibility with the Verifier agent.
    """
    try:
        steps = solver_out["solution_steps"]
        if not steps:
            return False
        last_text = str(steps[-1]["text"]).strip()
        m = _FINAL_ANSWER_RE.search(last_text)
        if not m:
            return False
        return m.group(1).strip() == str(solver_out["answer_canonical"][0]).strip()
    except Exception:
        return False


def _load_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def parse_solution_text(raw: str) -> JsonDict:
    """Parse numbered-step plain text into the SolverOutput dict.

    Accepts multi-line step text (continuation lines before the next
    ``StepN:`` or ``Answer:`` are appended to the current step).

    Returns a dict matching the ``SolverOutput`` schema::

        {
            "answer_canonical": ["<answer>"],
            "solution_steps": [
                {"step_id": "Step1", "text": "..."},
                ...
            ]
        }

    Raises ``ValueError`` if parsing fails.
    """
    steps: List[Tuple[int, str]] = []
    answer: str | None = None
    current_step_num: int | None = None
    current_lines: List[str] = []

    def _flush_step() -> None:
        nonlocal current_step_num, current_lines
        if current_step_num is not None and current_lines:
            steps.append((current_step_num, " ".join(current_lines)))
        current_step_num = None
        current_lines = []

    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        m_answer = _ANSWER_RE.match(line)
        if m_answer:
            _flush_step()
            answer = m_answer.group(1).strip()
            continue

        m_step = _STEP_RE.match(line)
        if m_step:
            _flush_step()
            current_step_num = int(m_step.group(1))
            current_lines = [m_step.group(2).strip()]
            continue

        # Continuation line for current step
        if current_step_num is not None:
            current_lines.append(line)

    _flush_step()

    if answer is None:
        raise ValueError(
            f"No 'Answer:' line found in solver output. Raw text:\n{raw[:500]}"
        )
    if not steps:
        raise ValueError(
            f"No 'StepN:' lines found in solver output. Raw text:\n{raw[:500]}"
        )

    # Build the last step text to include "Final answer: X" for downstream compatibility
    last_idx = len(steps) - 1
    step_text = steps[last_idx][1]
    if "final answer" not in step_text.lower():
        steps[last_idx] = (steps[last_idx][0], f"{step_text} Final answer: {answer}")

    solution_steps = [
        {"step_id": f"Step{num}", "text": text}
        for num, text in steps
    ]

    result = {
        "answer_canonical": [answer],
        "solution_steps": solution_steps,
    }

    # Validate against Pydantic schema
    SolverOutput.model_validate(result)

    return result


class Solver:
    def __init__(
        self,
        llm: LLMClient,
        prompt_path: str | Path = "prompts/v5_guided/solver.txt",
        domain_guide: str | None = None,
    ) -> None:
        self.llm = llm
        self.prompt_path = str(prompt_path)
        base = _load_text(self.prompt_path).strip()
        if domain_guide:
            self._system_prompt = domain_guide + "\n\n---\n\n" + base
        else:
            self._system_prompt = base

    def solve_item(self, item: JsonDict) -> JsonDict:
        """Solve one item: LLM free-text reasoning → Python parse to JSON."""
        import json

        item_text = json.dumps(item, ensure_ascii=False)

        raw = self.llm.chat_completions(
            [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": item_text},
            ],
            temperature=0.0,
        )

        return parse_solution_text(raw)
