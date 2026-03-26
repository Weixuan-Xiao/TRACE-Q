from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from schemas.solver_output import SolverOutput
from schemas.verifier_output import VerifierOutput
from src.agent_utils import call_json_with_validation, load_text
from src.llm_client import LLMClient
from src.solver import _is_internally_consistent

JsonDict = Dict[str, Any]


VERIFIER_SCHEMA_TEXT = """Return JSON with exactly:
{
  "ok": true/false,
  "issues": [{"type":"answer_mismatch|step_gap|logic_error|format_error|other","detail":"..."}],
  "corrected_solver": null OR {"answer_canonical":[...], "solution_steps":[{"step_id":"Step1","text":"..."},...]}
}
If ok=true => corrected_solver must be null.
If ok=false => corrected_solver must be provided and must satisfy:
- last solution step ends with 'Final answer: <ANSWER>'
- <ANSWER> equals corrected_solver.answer_canonical[0]
"""


def _extra_validate(verifier_out: JsonDict) -> Optional[str]:
    """
    Enforce corrected solver internal consistency when provided.
    """
    ok = bool(verifier_out.get("ok"))
    corrected = verifier_out.get("corrected_solver")
    if ok:
        if corrected is not None:
            return "ok=true but corrected_solver is not null"
        return None

    if corrected is None:
        return "ok=false but corrected_solver is null"
    # Ensure corrected_solver matches SolverOutput and is internally consistent.
    try:
        solver_dict = SolverOutput.model_validate(corrected).model_dump()
    except Exception as e:
        return f"corrected_solver does not match Solver schema: {e}"
    if not _is_internally_consistent(solver_dict):
        return "corrected_solver final answer does not match answer_canonical[0]"
    return None


class Verifier:
    def __init__(self, llm: LLMClient, prompt_path: str | Path = "prompts/v1/verifier.txt") -> None:
        self.llm = llm
        self.prompt_path = str(prompt_path)
        self._system_prompt = load_text(self.prompt_path)

    def verify(self, *, item: JsonDict, solver: JsonDict, max_fix_retries: int = 2) -> JsonDict:
        user_json = {"item": item, "solver": solver}
        return call_json_with_validation(
            llm=self.llm,
            system_prompt=self._system_prompt,
            user_json=user_json,
            model_cls=VerifierOutput,
            required_schema_text=VERIFIER_SCHEMA_TEXT,
            extra_validator=_extra_validate,
            max_fix_retries=max_fix_retries,
        )
