"""
Utilities for working with both flat and hierarchical codebooks.
"""
from __future__ import annotations

from typing import Any, Dict, List, Set

JsonDict = Dict[str, Any]


def is_hierarchical_codebook(codebook: JsonDict) -> bool:
    """Check if codebook is hierarchical (has 'hierarchy' key) or flat (has 'skills' key)."""
    return "hierarchy" in codebook


def extract_skill_ids(codebook: JsonDict) -> Set[str]:
    """
    Extract all L3 skill IDs from a codebook (works for both flat and hierarchical).
    
    For hierarchical: extracts all skill_ids from hierarchy.processes.skills
    For flat: extracts all skill_ids from skills list
    """
    if is_hierarchical_codebook(codebook):
        # Hierarchical codebook
        skill_ids = set()
        for domain in codebook.get("hierarchy", []):
            for process in domain.get("processes", []):
                for skill in process.get("skills", []):
                    sid = str(skill.get("skill_id", "")).strip()
                    if sid:
                        skill_ids.add(sid)
        return skill_ids
    else:
        # Flat codebook
        return {
            str(s.get("skill_id", "")).strip()
            for s in codebook.get("skills", [])
            if str(s.get("skill_id", "")).strip()
        }


def get_flat_skills_list(codebook: JsonDict) -> List[JsonDict]:
    """
    Get a flat list of all skills from a codebook (works for both formats).
    
    Returns list of dicts with skill_id, name, definition, etc.
    """
    if is_hierarchical_codebook(codebook):
        skills = []
        for domain in codebook.get("hierarchy", []):
            for process in domain.get("processes", []):
                for skill in process.get("skills", []):
                    skills.append(skill)
        return skills
    else:
        return codebook.get("skills", [])


def codebook_to_flat_format(codebook: JsonDict) -> JsonDict:
    """
    Convert a hierarchical codebook to flat format for backward compatibility.
    
    The flat format has: {"version": ..., "domain": ..., "skills": [...]}
    """
    if not is_hierarchical_codebook(codebook):
        return codebook
    
    flat_skills = []
    for domain in codebook.get("hierarchy", []):
        for process in domain.get("processes", []):
            for skill in process.get("skills", []):
                flat_skill = {
                    "skill_id": skill.get("skill_id", ""),
                    "name": skill.get("name", ""),
                    "definition": skill.get("definition", ""),
                    "inclusion_criteria": skill.get("inclusion_criteria", []),
                    "exclusion_criteria": skill.get("exclusion_criteria", []),
                    "examples": [],  # Flat format uses different example structure
                    "prerequisites": [],
                }
                flat_skills.append(flat_skill)
    
    return {
        "version": codebook.get("version", "v1"),
        "domain": codebook.get("domain", ""),
        "skills": flat_skills,
    }
