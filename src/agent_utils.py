from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Type

from pydantic import BaseModel, ValidationError

from src.llm_client import LLMClient

JsonDict = Dict[str, Any]

# Metadata keys injected by orchestration scripts (main.py, main_verify.py, etc.)
# that must NOT leak into LLM prompts — they change between runs and break
# reproducibility.
_METADATA_KEYS = frozenset({"created_at", "stage", "timestamp"})


def strip_metadata(obj: JsonDict) -> JsonDict:
    """Return a shallow copy of *obj* without run-dependent metadata keys."""
    return {k: v for k, v in obj.items() if k not in _METADATA_KEYS}


def slim_dossier_for_llm(dossier: JsonDict) -> JsonDict:
    """Return a compact dossier containing only the fields LLM agents need.

    Keeps: item_id, item.{item_id, stem_text}, solver.solution_steps[].{step_id, text}.
    Drops: answer_rules, answer_canonical, verifier, created_at, stage, timestamp.
    """
    item = dossier.get("item", {}) if isinstance(dossier.get("item"), dict) else {}
    solver = dossier.get("solver", {}) if isinstance(dossier.get("solver"), dict) else {}
    steps_raw = solver.get("solution_steps", [])
    steps = steps_raw if isinstance(steps_raw, list) else []

    return {
        "item_id": str(dossier.get("item_id", item.get("item_id", ""))).strip(),
        "item": {
            "item_id": str(item.get("item_id", "")).strip(),
            "stem_text": str(item.get("stem_text", "")),
        },
        "solver": {
            "solution_steps": [
                {"step_id": str(s.get("step_id", "")), "text": str(s.get("text", ""))}
                for s in steps
                if isinstance(s, dict)
            ],
        },
    }


FIX_JSON_SYSTEM_PROMPT = """You are a strict JSON repair tool.
Return ONLY a valid JSON object. Do not include explanations, markdown, or code fences.
"""


def load_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def load_guides(guides_dir: str | Path, filenames: list[str]) -> str | None:
    """Load and concatenate multiple guide files from *guides_dir*.

    Returns the concatenated text, or ``None`` if the directory does not
    exist or none of the requested files are found.
    """
    gdir = Path(guides_dir)
    if not gdir.is_dir():
        return None
    parts: list[str] = []
    for fname in filenames:
        p = gdir / fname
        if p.exists():
            parts.append(p.read_text(encoding="utf-8").strip())
    return "\n\n".join(parts) if parts else None


def try_parse_json(text: str) -> Tuple[Optional[JsonDict], Optional[str]]:
    try:
        return json.loads(text), None
    except Exception as e:
        return None, str(e)


def call_json_with_validation(
    *,
    llm: LLMClient,
    system_prompt: str,
    user_json: JsonDict,
    model_cls: Type[BaseModel],
    required_schema_text: str,
    extra_validator: Optional[Callable[[JsonDict], Optional[str]]] = None,
    max_fix_retries: int = 2,
) -> JsonDict:
    """
    LLM -> strict JSON -> pydantic validate -> optional extra validate.
    If invalid, run up to max_fix_retries repair attempts using the same model (LLM-only).
    """
    user_text = json.dumps(user_json, ensure_ascii=False)
    raw = llm.chat_completions(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    last_err: Optional[str] = None
    for i in range(0, max_fix_retries + 1):
        parsed, parse_err = try_parse_json(raw)
        if parsed is not None:
            try:
                validated = model_cls.model_validate(parsed).model_dump()
                if extra_validator is not None:
                    extra_err = extra_validator(validated)
                    if extra_err is None:
                        return validated
                    last_err = f"ExtraValidationError: {extra_err}"
                else:
                    return validated
            except ValidationError as ve:
                last_err = f"ValidationError: {ve}"
        else:
            last_err = f"JSONParseError: {parse_err}"

        if i >= max_fix_retries:
            raise RuntimeError(f"JSON output invalid after retries. Last error: {last_err}. Raw: {raw[:500]}")

        fix_user = {
            "required_schema": required_schema_text,
            "validation_error": last_err,
            "bad_output": raw,
        }
        raw = llm.chat_completions(
            [
                {"role": "system", "content": FIX_JSON_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(fix_user, ensure_ascii=False)},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )

    raise RuntimeError("Unexpected retry logic fallthrough.")


