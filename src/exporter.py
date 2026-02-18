"""
Q-Matrix Exporter for hierarchical skill codebooks.

Generates Q-matrices at three granularity levels:
- L1: Items x Domains (coarsest)
- L2: Items x Processes (medium)
- L3: Items x Skills (finest)
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Set

JsonDict = Dict[str, Any]


def extract_final_skill_ids(dossier: JsonDict) -> Set[str]:
    """Extract L3 skill IDs from judge's final_skills."""
    judge = dossier.get("judge", {})
    final = judge.get("final_skills", [])
    
    # Handle both formats: list of dicts with skill_id, or list of strings
    skill_ids = set()
    for item in final:
        if isinstance(item, dict):
            sid = str(item.get("skill_id", "")).strip()
        else:
            sid = str(item).strip()
        if sid:
            skill_ids.add(sid)
    
    return skill_ids


def build_level_mapping(codebook: JsonDict) -> Dict[str, Dict[str, str]]:
    """
    Build mapping from finer levels to coarser levels.
    
    Returns:
        {
            "L3_to_L2": {"S01": "P01", ...},
            "L2_to_L1": {"P01": "D01", ...}
        }
    """
    l3_to_l2: Dict[str, str] = {}
    l2_to_l1: Dict[str, str] = {}
    
    hierarchy = codebook.get("hierarchy", [])
    for domain in hierarchy:
        domain_id = domain.get("domain_id", "")
        for process in domain.get("processes", []):
            process_id = process.get("process_id", "")
            l2_to_l1[process_id] = domain_id
            for skill in process.get("skills", []):
                skill_id = skill.get("skill_id", "")
                l3_to_l2[skill_id] = process_id
    
    return {"L3_to_L2": l3_to_l2, "L2_to_L1": l2_to_l1}


def get_ids_by_level(codebook: JsonDict) -> Dict[str, List[str]]:
    """Get ordered list of IDs at each level."""
    hierarchy = codebook.get("hierarchy", [])
    
    l1_ids = [d.get("domain_id", "") for d in hierarchy]
    l2_ids = [
        p.get("process_id", "")
        for d in hierarchy
        for p in d.get("processes", [])
    ]
    l3_ids = [
        s.get("skill_id", "")
        for d in hierarchy
        for p in d.get("processes", [])
        for s in p.get("skills", [])
    ]
    
    return {"L1": l1_ids, "L2": l2_ids, "L3": l3_ids}


def aggregate_to_level(
    l3_skills: Set[str],
    target_level: int,
    mapping: Dict[str, Dict[str, str]],
) -> Set[str]:
    """
    Aggregate L3 skills to a coarser level.
    
    Args:
        l3_skills: Set of L3 skill IDs
        target_level: 1, 2, or 3
        mapping: Level mapping from build_level_mapping()
    
    Returns:
        Set of IDs at the target level
    """
    if target_level == 3:
        return l3_skills
    
    l3_to_l2 = mapping["L3_to_L2"]
    l2_to_l1 = mapping["L2_to_L1"]
    
    # L3 -> L2
    l2_ids = {l3_to_l2[s] for s in l3_skills if s in l3_to_l2}
    
    if target_level == 2:
        return l2_ids
    
    # L2 -> L1
    l1_ids = {l2_to_l1[p] for p in l2_ids if p in l2_to_l1}
    return l1_ids


def export_q_matrix(
    dossiers: List[JsonDict],
    codebook: JsonDict,
    level: int,
    output_path: Path,
) -> None:
    """
    Export Q-matrix CSV at the specified level.
    
    Args:
        dossiers: Adjudicated dossiers with judge.final_skills
        codebook: Hierarchical codebook
        level: 1, 2, or 3
        output_path: Path to write CSV
    """
    mapping = build_level_mapping(codebook)
    ids_by_level = get_ids_by_level(codebook)
    level_ids = ids_by_level[f"L{level}"]
    
    rows = []
    for dossier in dossiers:
        item_id = str(dossier.get("item_id", "")).strip()
        l3_skills = extract_final_skill_ids(dossier)
        level_skills = aggregate_to_level(l3_skills, level, mapping)
        
        row = {"item_id": item_id}
        for attr_id in level_ids:
            row[attr_id] = 1 if attr_id in level_skills else 0
        rows.append(row)
    
    # Write CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["item_id"] + level_ids)
        writer.writeheader()
        writer.writerows(rows)


def export_all_levels(
    dossiers: List[JsonDict],
    codebook: JsonDict,
    output_dir: Path,
    prefix: str = "Q_matrix",
) -> Dict[str, Path]:
    """
    Export Q-matrices at all three levels.
    
    Args:
        dossiers: Adjudicated dossiers
        codebook: Hierarchical codebook
        output_dir: Directory to write CSV files
        prefix: Filename prefix
        
    Returns:
        Dict mapping level name to output path
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    
    for level in [1, 2, 3]:
        output_path = output_dir / f"{prefix}_L{level}.csv"
        export_q_matrix(dossiers, codebook, level, output_path)
        outputs[f"L{level}"] = output_path
    
    return outputs


def get_attribute_info(codebook: JsonDict, level: int) -> List[Dict[str, str]]:
    """
    Get attribute information at the specified level.
    
    Returns list of dicts with id, name, definition.
    """
    hierarchy = codebook.get("hierarchy", [])
    
    if level == 1:
        return [
            {
                "id": d.get("domain_id", ""),
                "name": d.get("name", ""),
                "definition": d.get("description", ""),
            }
            for d in hierarchy
        ]
    elif level == 2:
        return [
            {
                "id": p.get("process_id", ""),
                "name": p.get("name", ""),
                "definition": p.get("description", ""),
                "parent": p.get("parent_domain_id", ""),
            }
            for d in hierarchy
            for p in d.get("processes", [])
        ]
    else:  # level == 3
        return [
            {
                "id": s.get("skill_id", ""),
                "name": s.get("name", ""),
                "definition": s.get("definition", ""),
                "observable_evidence": s.get("observable_evidence", ""),
                "parent": p.get("process_id", ""),
            }
            for d in hierarchy
            for p in d.get("processes", [])
            for s in p.get("skills", [])
        ]
