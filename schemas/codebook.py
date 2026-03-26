from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class SkillExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(..., min_length=1)
    step_ids: List[str] = Field(default_factory=list)


class Skill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(..., pattern=r"^S\d{2,3}$")
    name: str = Field(..., min_length=1)
    definition: str = Field(..., min_length=1)
    inclusion_criteria: List[str] = Field(default_factory=list)
    exclusion_criteria: List[str] = Field(default_factory=list)
    examples: List[SkillExample] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)


class Codebook(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="v1", pattern=r"^v\d+$")
    domain: str = Field(..., min_length=1)
    skills: List[Skill]


