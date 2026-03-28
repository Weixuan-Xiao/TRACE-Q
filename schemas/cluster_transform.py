from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class ClusterDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cluster_id: str = Field(..., pattern=r"^C\d{2,3}$")
    action: Literal["keep", "merge", "split", "relabel"]
    target_cluster_ids: List[str] = Field(default_factory=list)
    proposed_skill_names: List[str] = Field(default_factory=list)
    reasoning: str = Field(..., min_length=1)


class DraftSkillFromScaffold(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provisional_skill_id: str = Field(..., pattern=r"^DS\d{2,3}$")
    name: str = Field(..., min_length=1)
    definition: str = Field(..., min_length=1)
    source_cluster_ids: List[str] = Field(default_factory=list)
    inclusion_criteria: List[str] = Field(default_factory=list)
    exclusion_criteria: List[str] = Field(default_factory=list)


class ClusterTransformOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="v1", pattern=r"^v\d+$")
    expert_id: str = Field(..., min_length=1)
    decisions: List[ClusterDecision]
    draft_skills: List[DraftSkillFromScaffold] = Field(default_factory=list)
    summary: str = Field(..., min_length=1)
