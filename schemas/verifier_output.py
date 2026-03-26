from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.solver_output import SolverOutput


class VerifierIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["answer_mismatch", "step_gap", "logic_error", "format_error", "other"]
    detail: str = Field(..., min_length=1)


class VerifierOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    issues: List[VerifierIssue]
    corrected_solver: Optional[SolverOutput] = None

    @model_validator(mode="after")
    def _check_consistency(self) -> "VerifierOutput":
        if self.ok:
            # ok => no corrections
            if self.corrected_solver is not None:
                raise ValueError("ok=true requires corrected_solver=null")
        else:
            if self.corrected_solver is None:
                raise ValueError("ok=false requires corrected_solver to be provided")
            if len(self.issues) == 0:
                raise ValueError("ok=false requires at least one issue")
        return self


