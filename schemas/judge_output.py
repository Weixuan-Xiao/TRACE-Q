from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class FinalSkill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(..., min_length=1)
    evidence_step_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)


class JudgeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    final_skills: List[FinalSkill] = Field(default_factory=list)
    judge_notes: str = Field(..., min_length=1)


