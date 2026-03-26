"""Pydantic schema for Auditor output."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Corrections(BaseModel):
    """Correction suggestions from the Auditor."""

    model_config = ConfigDict(extra="forbid")

    add_skills: List[str] = Field(default_factory=list)
    remove_skills: List[str] = Field(default_factory=list)
    reasoning: str = Field(..., min_length=1)


class AuditorOutput(BaseModel):
    """Schema for a single item's audit result."""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(..., min_length=1)
    auditor_skills: List[str] = Field(default_factory=list)
    verdict: Literal["correct", "error", "controversial"] = Field(...)
    controversy_flags: List[str] = Field(default_factory=list)
    corrections: Corrections = Field(...)

