from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ReasoningCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(..., min_length=1)
    stem_text: str = Field(default="")
    solution_summary: str = Field(default="")
    step_texts: List[str] = Field(default_factory=list)
