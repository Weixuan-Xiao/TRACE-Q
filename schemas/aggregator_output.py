"""
Aggregator Output Schema.

The Aggregator merges fine-grained skills into coarser versions
to produce multiple K-level codebooks from a single detailed codebook.
"""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field


class MergedSkill(BaseModel):
    """A skill created by merging multiple finer-grained skills."""
    model_config = ConfigDict(extra="forbid")

    merged_id: str = Field(..., pattern=r"^M\d{2}$", description="ID for merged skill")
    name: str = Field(..., min_length=2, max_length=100)
    definition: str = Field(..., min_length=10)
    original_skill_ids: List[str] = Field(
        ..., 
        min_length=1,
        description="IDs of original skills that were merged into this one"
    )
    merge_rationale: str = Field(
        ..., 
        min_length=10,
        description="Why these skills were merged together"
    )


class AggregatedCodebook(BaseModel):
    """A codebook at a specific K level, created by merging."""
    model_config = ConfigDict(extra="forbid")

    target_k: int = Field(..., ge=2, le=20, description="The target K for this version")
    skills: List[MergedSkill] = Field(..., min_length=2)
    mapping: Dict[str, str] = Field(
        ...,
        description="Mapping from original skill_id to merged_id"
    )


class AggregatorOutput(BaseModel):
    """
    Complete output from the Aggregator agent.
    
    Contains the original codebook reference and multiple coarser versions.
    """
    model_config = ConfigDict(extra="forbid")

    source_k: int = Field(..., description="K of the source (finest) codebook")
    target_k_values: List[int] = Field(..., description="List of target K values generated")
    aggregated_codebooks: List[AggregatedCodebook] = Field(
        ...,
        description="Codebooks at each target K level"
    )
    aggregation_notes: str = Field(
        default="",
        description="Overall notes about the aggregation process"
    )
