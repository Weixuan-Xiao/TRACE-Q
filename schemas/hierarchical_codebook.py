"""
Hierarchical Codebook Schema.

Defines a three-level skill taxonomy:
- Level 1 (L1): Cognitive Domains (coarsest, K=3-5)
- Level 2 (L2): Cognitive Processes (medium, K=5-10)
- Level 3 (L3): Observable Skills/Operations (finest, K=8-15)
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Level3Skill(BaseModel):
    """Level 3: Observable skill/operation (finest granularity)"""
    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(..., pattern=r"^S\d{2,3}$", examples=["S01", "S02"])
    name: str = Field(..., min_length=2, max_length=80)
    definition: str = Field(..., min_length=10)
    observable_evidence: str = Field(
        ...,
        min_length=10,
        description="How to identify this skill in solution steps"
    )
    inclusion_criteria: List[str] = Field(default_factory=list)
    exclusion_criteria: List[str] = Field(default_factory=list)
    examples: List[str] = Field(
        default_factory=list, 
        max_length=5,
        description="Example step texts demonstrating this skill"
    )


class Level2Process(BaseModel):
    """Level 2: Cognitive process (medium granularity)"""
    model_config = ConfigDict(extra="forbid")

    process_id: str = Field(..., pattern=r"^P\d{2}$", examples=["P01", "P02"])
    name: str = Field(..., min_length=2, max_length=80)
    description: str = Field(..., min_length=10)
    parent_domain_id: str = Field(..., pattern=r"^D\d{2}$")
    skills: List[Level3Skill] = Field(..., min_length=1, max_length=5)


class Level1Domain(BaseModel):
    """Level 1: Cognitive domain (coarsest granularity)"""
    model_config = ConfigDict(extra="forbid")

    domain_id: str = Field(..., pattern=r"^D\d{2}$", examples=["D01", "D02"])
    name: str = Field(..., min_length=2, max_length=80)
    description: str = Field(..., min_length=10)
    processes: List[Level2Process] = Field(..., min_length=1, max_length=5)


class MergeDecision(BaseModel):
    """Record of a merge decision made by the Supervisor"""
    model_config = ConfigDict(extra="forbid")

    merged_items: List[str] = Field(..., min_length=2, description="IDs that were merged")
    into_id: str = Field(..., description="The resulting ID after merge")
    rationale: str = Field(..., min_length=10)


class HierarchicalCodebook(BaseModel):
    """
    Complete hierarchical skill codebook with three levels.
    
    This codebook supports multiple granularities of Q-matrix:
    - Q_L1: Items × Level 1 Domains
    - Q_L2: Items × Level 2 Processes
    - Q_L3: Items × Level 3 Skills
    """
    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="v1", pattern=r"^v\d+$")
    domain: str = Field(..., min_length=1, description="Subject area")
    
    # The hierarchy
    hierarchy: List[Level1Domain] = Field(..., min_length=2, max_length=5)
    
    # Metadata about merge decisions (populated by Supervisor)
    merge_decisions: List[MergeDecision] = Field(default_factory=list)
    validation_notes: str = Field(default="", description="Notes from validation/consolidation")
    
    # Auto-computed statistics
    k_by_level: Dict[str, int] = Field(
        default_factory=dict,
        description="Number of attributes at each level: {'L1': 3, 'L2': 7, 'L3': 12}"
    )

    @model_validator(mode='after')
    def compute_k_values(self) -> 'HierarchicalCodebook':
        """Compute K values for each level after validation."""
        l1_count = len(self.hierarchy)
        l2_count = sum(len(d.processes) for d in self.hierarchy)
        l3_count = sum(
            len(p.skills) 
            for d in self.hierarchy 
            for p in d.processes
        )
        self.k_by_level = {"L1": l1_count, "L2": l2_count, "L3": l3_count}
        return self

    def get_flat_skills(self, level: int = 3) -> List[dict]:
        """
        Get a flat list of skills/attributes at the specified level.
        
        Args:
            level: 1, 2, or 3
            
        Returns:
            List of dicts with id, name, definition, and parent info
        """
        if level == 1:
            return [
                {
                    "id": d.domain_id, 
                    "name": d.name, 
                    "definition": d.description
                }
                for d in self.hierarchy
            ]
        elif level == 2:
            return [
                {
                    "id": p.process_id, 
                    "name": p.name, 
                    "definition": p.description,
                    "parent_domain_id": p.parent_domain_id
                }
                for d in self.hierarchy 
                for p in d.processes
            ]
        else:  # level == 3
            return [
                {
                    "id": s.skill_id, 
                    "name": s.name, 
                    "definition": s.definition,
                    "observable_evidence": s.observable_evidence,
                    "parent_process_id": p.process_id
                }
                for d in self.hierarchy 
                for p in d.processes 
                for s in p.skills
            ]

    def get_level_mapping(self) -> Dict[str, Dict[str, str]]:
        """
        Get mapping from finer levels to coarser levels.
        
        Returns:
            {
                "L3_to_L2": {"S01": "P01", "S02": "P01", ...},
                "L2_to_L1": {"P01": "D01", "P02": "D01", ...}
            }
        """
        l3_to_l2: Dict[str, str] = {}
        l2_to_l1: Dict[str, str] = {}
        
        for d in self.hierarchy:
            for p in d.processes:
                l2_to_l1[p.process_id] = d.domain_id
                for s in p.skills:
                    l3_to_l2[s.skill_id] = p.process_id
        
        return {"L3_to_L2": l3_to_l2, "L2_to_L1": l2_to_l1}

    def get_all_skill_ids(self, level: int = 3) -> List[str]:
        """Get ordered list of all IDs at the specified level."""
        if level == 1:
            return [d.domain_id for d in self.hierarchy]
        elif level == 2:
            return [p.process_id for d in self.hierarchy for p in d.processes]
        else:
            return [s.skill_id for d in self.hierarchy for p in d.processes for s in p.skills]


# Alias for backward compatibility with flat codebook usage
Codebook = HierarchicalCodebook
