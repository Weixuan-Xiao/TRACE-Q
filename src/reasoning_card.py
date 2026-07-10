from __future__ import annotations

import re
from typing import Any, Dict, List

from schemas.reasoning_card import ReasoningCard

JsonDict = Dict[str, Any]


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_stem_text(item: JsonDict) -> str:
    for key in ["stem_text", "question", "prompt", "text", "item_text"]:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return _compact_text(value)
    return ""


def _extract_step_texts(solver: JsonDict) -> List[str]:
    step_texts: List[str] = []
    raw_steps = solver.get("solution_steps", [])
    if not isinstance(raw_steps, list):
        return step_texts

    for step in raw_steps:
        if isinstance(step, str):
            text = _compact_text(step)
            if text:
                step_texts.append(text)
            continue
        if not isinstance(step, dict):
            continue
        for key in ["text", "description", "content", "summary", "step_text"]:
            value = step.get(key)
            if isinstance(value, str) and value.strip():
                step_texts.append(_compact_text(value))
                break
    return step_texts


def _extract_solution_summary(solver: JsonDict, step_texts: List[str]) -> str:
    for key in ["final_answer_explanation", "solution_summary", "summary", "rationale"]:
        value = solver.get(key)
        if isinstance(value, str) and value.strip():
            return _compact_text(value)
    if step_texts:
        return _compact_text(" ".join(step_texts[:3]))
    return ""


def build_reasoning_card(dossier: JsonDict) -> JsonDict:
    """Build a domain-agnostic reasoning card from a verified dossier."""
    item = dossier.get("item", {}) if isinstance(dossier.get("item"), dict) else {}
    solver = dossier.get("solver", {}) if isinstance(dossier.get("solver"), dict) else {}

    item_id = str(dossier.get("item_id", item.get("item_id", ""))).strip()
    stem_text = _extract_stem_text(item)
    step_texts = _extract_step_texts(solver)
    solution_summary = _extract_solution_summary(solver, step_texts)

    card = ReasoningCard(
        item_id=item_id,
        stem_text=stem_text,
        solution_summary=solution_summary,
        step_texts=step_texts,
    )
    return card.model_dump()
