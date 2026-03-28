from __future__ import annotations

import re
from typing import Any, Dict, List

from schemas.reasoning_card import ReasoningCard

JsonDict = Dict[str, Any]

_TAG_PATTERNS: dict[str, list[str]] = {
    "solve_equation": [r"\bequation\b", r"\bsolve\b", r"\broot\b", r"\bquadratic\b"],
    "simplify_expression": [r"\bsimplif", r"\bexpand\b", r"\bfactor\b", r"\bsubstitut"],
    "counting": [r"\bcount\b", r"\bhow many\b", r"\barrange\b", r"\bchoose\b", r"\bways\b"],
    "probability": [r"\bprobability\b", r"\bindependent\b", r"\bchance\b", r"\bdice\b"],
    "geometry": [r"\btriangle\b", r"\bcircle\b", r"\bangle\b", r"\bplane\b", r"\bperimeter\b"],
    "function": [r"\bfunction\b", r"\bgraph\b", r"\bdomain\b", r"\brange\b", r"\bvertex\b"],
    "matrix_vector": [r"\bmatrix\b", r"\bdeterminant\b", r"\bvector\b", r"\bplane\b"],
    "number_theory": [r"\bmod\b", r"\bcongruence\b", r"\bdivisib", r"\bprime\b", r"\bgcd\b"],
    "optimization": [r"\bminimum\b", r"\bmaximum\b", r"\boptimi", r"\binequality\b"],
    "recursion_sequence": [r"\brecursive\b", r"\bsequence\b", r"\bseries\b", r"\biterate\b"],
    "complex_numbers": [r"\bcomplex\b", r"\bimaginary\b", r"\b\bi\b", r"\broot of unity\b"],
    "word_problem": [r"\bpercent\b", r"\bratio\b", r"\bmixture\b", r"\bstudent\b", r"\bcandy\b"],
}


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


def infer_operation_tags(stem_text: str, solution_summary: str, step_texts: List[str]) -> List[str]:
    joined = " ".join([stem_text, solution_summary, *step_texts]).lower()
    tags: List[str] = []
    for tag, patterns in _TAG_PATTERNS.items():
        if any(re.search(pattern, joined) for pattern in patterns):
            tags.append(tag)
    if not tags:
        tags.append("misc")
    return sorted(set(tags))


def build_reasoning_card(dossier: JsonDict) -> JsonDict:
    item = dossier.get("item", {}) if isinstance(dossier.get("item"), dict) else {}
    solver = dossier.get("solver", {}) if isinstance(dossier.get("solver"), dict) else {}

    item_id = str(dossier.get("item_id", item.get("item_id", ""))).strip()
    stem_text = _extract_stem_text(item)
    step_texts = _extract_step_texts(solver)
    solution_summary = _extract_solution_summary(solver, step_texts)
    operation_tags = infer_operation_tags(stem_text, solution_summary, step_texts)
    structural_signature = "|".join(operation_tags)

    card = ReasoningCard(
        item_id=item_id,
        stem_text=stem_text,
        solution_summary=solution_summary,
        step_texts=step_texts,
        operation_tags=operation_tags,
        structural_signature=structural_signature,
    )
    return card.model_dump()
