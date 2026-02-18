from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Type

from pydantic import BaseModel, ValidationError

from src.llm_client import LLMClient

JsonDict = Dict[str, Any]


FIX_JSON_SYSTEM_PROMPT = """You are a strict JSON repair tool.
Return ONLY a valid JSON object. Do not include explanations, markdown, or code fences.
"""


def load_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


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


