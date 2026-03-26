from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class SolutionStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)


class SolverOutput(BaseModel):
    """
    Expected strict JSON shape:
    {
      "answer_canonical":[...],
      "solution_steps":[{"step_id":"Step1","text":"..."},...]
    }
    """

    model_config = ConfigDict(extra="forbid")

    answer_canonical: List[str]
    solution_steps: List[SolutionStep]


