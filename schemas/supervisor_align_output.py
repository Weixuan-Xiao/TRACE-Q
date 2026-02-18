"""
Schema for Supervisor Align output.

The Supervisor Align phase identifies semantically equivalent skills across
multiple expert codebooks and produces a standardized candidate skill list.
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class CandidateSkill(BaseModel):
    """A candidate skill identified by aligning multiple expert codebooks."""
    model_config = ConfigDict(extra="forbid")

    canonical_id: str = Field(
        ..., pattern=r"^C\d{2,3}$",
        description="Canonical ID for this candidate skill (C01, C02, ...)"
    )
    canonical_name: str = Field(..., min_length=2, max_length=100)
    canonical_definition: str = Field(..., min_length=10)
    expert_a_skill_ids: List[str] = Field(
        default_factory=list,
        description="Skill IDs from Expert A that map to this candidate (empty if not present)"
    )
    expert_b_skill_ids: List[str] = Field(
        default_factory=list,
        description="Skill IDs from Expert B that map to this candidate (empty if not present)"
    )
    expert_c_skill_ids: List[str] = Field(
        default_factory=list,
        description="Skill IDs from Expert C that map to this candidate (empty if not present)"
    )
    consensus: str = Field(
        ..., pattern=r"^[123]/3$",
        description="How many experts identified this skill concept: 3/3, 2/3, or 1/3"
    )
    alignment_notes: str = Field(
        default="",
        description="Notes on how this alignment was determined"
    )


class SupervisorAlignOutput(BaseModel):
    """
    Output from the Supervisor Align phase.

    Contains a list of candidate skills with alignment mappings across experts.
    """
    model_config = ConfigDict(extra="forbid")

    candidate_skills: List[CandidateSkill] = Field(
        ..., min_length=1,
        description="Standardized candidate skill list with alignment info"
    )
    alignment_summary: str = Field(
        ..., min_length=1,
        description="Summary of the alignment process and key observations"
    )
