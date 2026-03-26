"""
Aggregator Agent: Creates coarser skill codebooks by merging skills.

Given a fine-grained codebook (K=K_max), produces multiple coarser versions
(e.g., K=6, K=5, K=4) by semantically merging related skills.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from schemas.aggregator_output import AggregatorOutput, AggregatedCodebook
from src.agent_utils import call_json_with_validation, load_text
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]


AGGREGATOR_SCHEMA_TEXT = """Return JSON with exactly:
{
  "source_k": <int>,
  "target_k_values": [<int>, ...],
  "aggregated_codebooks": [
    {
      "target_k": <int>,
      "skills": [
        {
          "merged_id": "M01",
          "name": "...",
          "definition": "...",
          "original_skill_ids": ["S01", "S02"],
          "merge_rationale": "..."
        }
      ],
      "mapping": {"S01": "M01", "S02": "M01", ...}
    }
  ],
  "aggregation_notes": "..."
}
No extra keys.
"""


class Aggregator:
    """
    Aggregator Agent for creating multi-K codebooks.
    
    Takes a fine-grained codebook and produces coarser versions
    by merging semantically related skills.
    """

    def __init__(
        self,
        llm: LLMClient,
        prompt_path: str | Path = "prompts/v2/aggregator.txt",
    ) -> None:
        self.llm = llm
        self.prompt_path = str(prompt_path)
        self._system_prompt = load_text(self.prompt_path)

    def aggregate(
        self,
        *,
        codebook: JsonDict,
        target_k_values: List[int],
        dossiers: List[JsonDict],
        max_fix_retries: int = 2,
    ) -> JsonDict:
        """
        Create coarser versions of the codebook.
        
        Args:
            codebook: Fine-grained skill codebook
            target_k_values: List of target K values (e.g., [6, 5, 4])
            dossiers: Item dossiers for context
            max_fix_retries: Max retries for JSON repair
            
        Returns:
            AggregatorOutput as dict
        """
        # Extract skill info from codebook
        skills = codebook.get("skills", [])
        source_k = len(skills)
        
        # Prepare dossiers summary
        dossiers_summary = [
            {
                "item_id": d.get("item_id", ""),
                "stem_text": d.get("item", {}).get("stem_text", ""),
                "solution_steps": d.get("solver", {}).get("solution_steps", []),
            }
            for d in dossiers[:10]  # Limit to first 10 for token efficiency
        ]
        
        # Sort target_k_values descending (merge progressively)
        sorted_targets = sorted([k for k in target_k_values if k < source_k], reverse=True)
        
        user_json = {
            "codebook": codebook,
            "source_k": source_k,
            "target_k_values": sorted_targets,
            "dossiers_sample": dossiers_summary,
        }
        
        result = call_json_with_validation(
            llm=self.llm,
            system_prompt=self._system_prompt,
            user_json=user_json,
            model_cls=AggregatorOutput,
            required_schema_text=AGGREGATOR_SCHEMA_TEXT,
            extra_validator=lambda x: self._validate_aggregation(x, skills),
            max_fix_retries=max_fix_retries,
        )
        
        return result

    def _validate_aggregation(
        self, 
        output: JsonDict, 
        original_skills: List[JsonDict],
    ) -> Optional[str]:
        """
        Validate the aggregation output.
        
        Returns None if valid, error message if invalid.
        """
        original_ids = {s.get("skill_id") for s in original_skills}
        
        for agg_codebook in output.get("aggregated_codebooks", []):
            mapping = agg_codebook.get("mapping", {})
            
            # Check all original skills are mapped
            mapped_ids = set(mapping.keys())
            if mapped_ids != original_ids:
                missing = original_ids - mapped_ids
                extra = mapped_ids - original_ids
                if missing:
                    return f"Missing skills in mapping: {missing}"
                if extra:
                    return f"Unknown skills in mapping: {extra}"
            
            # Check merged IDs exist in skills
            skills = agg_codebook.get("skills", [])
            merged_ids = {s.get("merged_id") for s in skills}
            mapped_targets = set(mapping.values())
            
            if mapped_targets != merged_ids:
                return f"Mapping targets {mapped_targets} don't match skill IDs {merged_ids}"
            
            # Check target_k matches actual skill count
            target_k = agg_codebook.get("target_k")
            if len(skills) != target_k:
                return f"target_k={target_k} but {len(skills)} skills defined"
        
        return None


def apply_mapping_to_q_vector(
    q_vector: Dict[str, int],
    mapping: Dict[str, str],
) -> Dict[str, int]:
    """
    Apply skill mapping to a Q-vector.
    
    If any original skill in a merged group is 1, the merged skill is 1.
    
    Args:
        q_vector: Original Q-vector {skill_id: 0/1}
        mapping: Mapping from original to merged IDs
        
    Returns:
        New Q-vector with merged IDs
    """
    merged_q: Dict[str, int] = {}
    
    for orig_id, merged_id in mapping.items():
        if merged_id not in merged_q:
            merged_q[merged_id] = 0
        # OR logic: if any original skill is 1, merged is 1
        if q_vector.get(orig_id, 0) == 1:
            merged_q[merged_id] = 1
    
    return merged_q
