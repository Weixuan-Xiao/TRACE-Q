from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pydantic import ValidationError

from schemas.solver_output import SolverOutput
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]


FIX_JSON_SYSTEM_PROMPT = """You are a strict JSON repair tool.
You will be given:
1) A required JSON schema (in plain English).
2) An invalid or non-conforming model output.

Return ONLY a valid JSON object that conforms EXACTLY to the schema.
Do not include explanations, markdown, or code fences.
"""


FIX_JSON_USER_TEMPLATE = """Required schema:
Return a single JSON object with exactly these keys:
- "answer_canonical": an array of strings
- "solution_steps": an array of objects, each with exactly:
  - "step_id": string
  - "text": string

Invalid/non-conforming output:
{bad_text}

If you need to infer missing fields, do so conservatively.
Return ONLY the corrected JSON object.
"""


CONSISTENCY_SYSTEM_PROMPT = """You are a strict JSON post-processor for an exam-solving system.
You will be given:
1) The original item JSON (the problem).
2) A candidate solver JSON output that already matches the required schema.

Your task is to enforce INTERNAL CONSISTENCY ONLY:
- The LAST solution step must end with: "Final answer: <ANSWER>"
- The string <ANSWER> must EXACTLY MATCH answer_canonical[0]
- If multiple acceptable canonical answers are provided, keep them, but ensure answer_canonical[0] is the one used in the last step.

Do NOT add extra keys. Do NOT add commentary. Return ONLY the corrected JSON object.
If the candidate output is already consistent, return it unchanged.
"""


CONSISTENCY_USER_TEMPLATE = """Item JSON:
{item_json}

Candidate solver JSON:
{solver_json}

Return ONLY the corrected solver JSON, fully valid JSON.
"""


def _load_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _try_parse_json(text: str) -> Tuple[Optional[JsonDict], Optional[str]]:
    try:
        return json.loads(text), None
    except Exception as e:
        return None, str(e)


_FINAL_ANSWER_RE = re.compile(r"Final answer:\s*(.+?)\s*$")


def _is_internally_consistent(solver_out: JsonDict) -> bool:
    """
    Consistency rule:
    - last solution step text must end with `Final answer: <ANSWER>`
    - <ANSWER> must exactly equal answer_canonical[0]
    
    Note: This is a FORMAT check only. Correctness of the answer
    is validated by the Verifier agent.
    """
    try:
        steps = solver_out["solution_steps"]
        if not steps:
            return False
        last_text = str(steps[-1]["text"]).strip()
        m = _FINAL_ANSWER_RE.search(last_text)
        if not m:
            return False
        final_answer = m.group(1).strip()
        canon = solver_out["answer_canonical"]
        if not canon:
            return False
        canon0 = str(canon[0]).strip()
        return final_answer == canon0
    except Exception:
        return False


class Solver:
    def __init__(self, llm: LLMClient, prompt_path: str | Path = "prompts/v1/solver.txt") -> None:
        self.llm = llm
        self.prompt_path = str(prompt_path)
        self._system_prompt = _load_text(self.prompt_path).strip()

    def solve_item(self, item: JsonDict, *, max_fix_retries: int = 2) -> JsonDict:
        """
        Returns validated solver output as dict.
        - If schema-invalid, retries up to max_fix_retries using a "fix JSON" prompt.
        - If internally inconsistent (Final answer != answer_canonical[0]),
          repairs using an LLM-only consistency fix pass.
        
        Note: Answer correctness is NOT checked here. That's the Verifier's job.
        """
        item_json = json.dumps(item, ensure_ascii=False)

        # 1) First attempt: normal solver prompt
        raw = self.llm.chat_completions(
            [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": item_json},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        for fix_attempt in range(0, max_fix_retries + 1):
            parsed, parse_err = _try_parse_json(raw)
            if parsed is not None:
                try:
                    validated = SolverOutput.model_validate(parsed).model_dump()
                    
                    # Check format consistency only
                    if _is_internally_consistent(validated):
                        return validated

                    # Consistency repair pass (format only)
                    repaired_raw = self.llm.chat_completions(
                        [
                            {"role": "system", "content": CONSISTENCY_SYSTEM_PROMPT},
                            {
                                "role": "user",
                                "content": CONSISTENCY_USER_TEMPLATE.format(
                                    item_json=item_json,
                                    solver_json=json.dumps(validated, ensure_ascii=False),
                                ),
                            },
                        ],
                        temperature=0.0,
                        response_format={"type": "json_object"},
                    )
                    raw = repaired_raw

                    repaired_parsed, repaired_err = _try_parse_json(repaired_raw)
                    if repaired_parsed is None:
                        parse_err = f"Consistency repair JSON parse error: {repaired_err}"
                    else:
                        repaired_validated = SolverOutput.model_validate(repaired_parsed).model_dump()
                        if _is_internally_consistent(repaired_validated):
                            return repaired_validated
                        parse_err = "Consistency repair produced output that is still inconsistent."
                except ValidationError as ve:
                    parse_err = f"ValidationError: {ve}"

            if fix_attempt >= max_fix_retries:
                raise RuntimeError(
                    "Solver output invalid after retries. "
                    f"Last error: {parse_err}. Raw: {raw[:500]}"
                )

            # 2) Fix attempts: ask model to repair to strict schema
            raw = self.llm.chat_completions(
                [
                    {"role": "system", "content": FIX_JSON_SYSTEM_PROMPT},
                    {"role": "user", "content": FIX_JSON_USER_TEMPLATE.format(bad_text=raw)},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )

        raise RuntimeError("Unexpected solver retry logic fallthrough.")
