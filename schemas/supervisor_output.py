"""
Schema for Supervisor output.

The Supervisor consolidates multiple expert codebooks into a unified flat codebook.
Supports both:
- Legacy single-phase consolidation (SupervisorOutput)
- Two-phase approach: align (SupervisorAlignOutput) + consolidate (SupervisorConsolidateOutput)
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SkillAlignment(BaseModel):
    """Alignment of a skill across multiple experts (legacy single-phase)."""
    model_config = ConfigDict(extra="forbid")

    final_skill_id: str = Field(..., min_length=1)
    expert_a: Optional[str] = None
    expert_b: Optional[str] = None
    expert_c: Optional[str] = None
    consensus: str = Field(..., pattern=r"^[123]/3$")


class SupervisorDecision(BaseModel):
    """A decision made during consolidation."""
    model_config = ConfigDict(extra="forbid")

    action: str = Field(..., pattern=r"^(merge|keep|remove|rename|refine)$")
    details: str = Field(..., min_length=1)
    reasoning: str = Field(..., min_length=1)


class SkillExample(BaseModel):
    """Example of a skill."""
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(..., min_length=1)
    step_ids: List[str] = Field(default_factory=list)


class FinalSkill(BaseModel):
    """A skill in the final codebook."""
    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(..., pattern=r"^S\d+$")
    name: str = Field(..., min_length=1)
    definition: str = Field(..., min_length=1)
    inclusion_criteria: List[str] = Field(default_factory=list)
    exclusion_criteria: List[str] = Field(default_factory=list)
    examples: List[SkillExample] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)


class FinalCodebook(BaseModel):
    """Final consolidated codebook."""
    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="v1")
    domain: str = Field(..., min_length=1)
    skills: List[FinalSkill] = Field(..., min_length=2, max_length=10)


class SupervisorOutput(BaseModel):
    """
    Legacy single-phase Supervisor output.

    Contains the final unified codebook plus alignment and decision metadata.
    """
    model_config = ConfigDict(extra="forbid")

    final_codebook: FinalCodebook
    alignment: List[SkillAlignment] = Field(default_factory=list)
    decisions: List[SupervisorDecision] = Field(default_factory=list)
    summary: str = Field(..., min_length=1)


class SupervisorConsolidateOutput(BaseModel):
    """
    Output from the Supervisor Consolidate phase (two-phase approach).

    Contains the final codebook plus decision records. Alignment info is
    provided separately by the Supervisor Align phase.
    """
    model_config = ConfigDict(extra="forbid")

    final_codebook: FinalCodebook
    decisions: List[SupervisorDecision] = Field(default_factory=list)
    summary: str = Field(..., min_length=1)
