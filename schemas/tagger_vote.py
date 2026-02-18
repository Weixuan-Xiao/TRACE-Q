from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class SkillTag(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(..., min_length=1)
    evidence_step_ids: List[str] = Field(default_factory=list)
    reasoning: str = Field(..., min_length=1, description="Explanation of why this skill is necessary")


class OptionalSkill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)


class TaggerVote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: List[SkillTag] = Field(default_factory=list)
    optional_skills: List[OptionalSkill] = Field(default_factory=list)
