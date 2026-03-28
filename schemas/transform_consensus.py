from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConsensusDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cluster_id: str = Field(..., pattern=r"^C\d{2,3}$")
    consensus_action: Literal["keep", "merge", "split", "relabel", "disputed"]
    agreement: str = Field(..., min_length=1)
    vote_counts: dict[str, int] = Field(default_factory=dict)
    target_cluster_ids: List[str] = Field(default_factory=list)
    proposed_skill_names: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class ConsensusDraftSkill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provisional_skill_id: str = Field(..., pattern=r"^CDS\d{2,3}$")
    name: str = Field(..., min_length=1)
    definition: str = Field(..., min_length=1)
    source_cluster_ids: List[str] = Field(default_factory=list)
    support_count: int = Field(..., ge=1)
    inclusion_criteria: List[str] = Field(default_factory=list)
    exclusion_criteria: List[str] = Field(default_factory=list)


class TransformConsensus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="v1", pattern=r"^v\d+$")
    recommended_final_k: int = Field(..., ge=1)
    consensus_decisions: List[ConsensusDecision]
    draft_skill_candidates: List[ConsensusDraftSkill] = Field(default_factory=list)
    disputed_clusters: List[str] = Field(default_factory=list)
    summary: str = Field(..., min_length=1)
