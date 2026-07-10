from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ScaffoldExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(..., min_length=1)
    step_ids: List[str] = Field(default_factory=list)
    note: str = Field(default="")


class ScaffoldCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cluster_id: str = Field(..., pattern=r"^C\d{2,3}$")
    provisional_skill_name: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1)
    distinguishing_terms: List[str] = Field(default_factory=list)
    representative_items: List[ScaffoldExample] = Field(default_factory=list)
    boundary_notes: List[str] = Field(default_factory=list)
    item_ids: List[str] = Field(default_factory=list)


class ScaffoldBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="v1", pattern=r"^v\d+$")
    domain: str = Field(..., min_length=1)
    source_stage: str = Field(default="structure_discovery", min_length=1)
    proposed_k: int = Field(..., ge=1)
    clusters: List[ScaffoldCluster]
    global_notes: List[str] = Field(default_factory=list)
