"""
Expert Agent: Domain expert for skill codebook generation.

Multiple Expert instances run in parallel to generate independent flat codebooks
with K=3-8 skills. These are then consolidated by the Supervisor.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from schemas.codebook import Codebook
from src.agent_utils import call_json_with_validation, load_text
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]


EXPERT_SCHEMA_TEXT = """Return JSON with exactly:
{
  "version": "v1",
  "domain": "<string>",
  "skills": [
    {
      "skill_id": "S01",
      "name": "...",
      "definition": "...",
      "inclusion_criteria": [...],
      "exclusion_criteria": [...],
      "examples": [{"item_id": "...", "step_ids": ["..."]}],
      "prerequisites": [...]
    }
  ]
}
No extra keys. You MUST define exactly 3-8 skills.
"""


class Expert:
    """
    Expert Agent for flat skill codebook generation.
    
    Generates a codebook with 3-8 skills based on analysis of the items.
    Multiple Experts run in parallel for stability.
    """

    def __init__(
        self,
        llm: LLMClient,
        expert_id: str = "A",
        prompt_path: str | Path | None = None,
        prompt_text: str | None = None,
    ) -> None:
        self.llm = llm
        self.expert_id = expert_id
        if prompt_text is not None:
            base_prompt = prompt_text
        elif prompt_path is not None:
            base_prompt = load_text(prompt_path)
        else:
            raise ValueError("Either prompt_path or prompt_text must be provided")
        self.prompt_path = str(prompt_path) if prompt_path else None
        self._system_prompt = base_prompt

    def build_codebook(
        self,
        *,
        verified_dossiers: List[JsonDict],
        max_fix_retries: int = 2,
    ) -> JsonDict:
        """
        Generate a flat skill codebook from verified dossiers.
        
        Args:
            verified_dossiers: List of verified item dossiers
            max_fix_retries: Max retries for JSON repair
            
        Returns:
            Codebook as dict with 3-8 skills
        """
        user_json = {"verified_dossiers": verified_dossiers}
        
        codebook = call_json_with_validation(
            llm=self.llm,
            system_prompt=self._system_prompt,
            user_json=user_json,
            model_cls=Codebook,
            required_schema_text=EXPERT_SCHEMA_TEXT,
            extra_validator=self._validate_skill_count,
            max_fix_retries=max_fix_retries,
        )
        
        if "version" not in codebook:
            codebook["version"] = "v1"
        
        return codebook

    def _validate_skill_count(self, codebook: JsonDict) -> Optional[str]:
        """
        Validate that codebook has 3-8 skills.
        
        Returns None if valid, error message if invalid.
        """
        skills = codebook.get("skills", [])
        n_skills = len(skills)
        
        if n_skills < 3:
            return f"Too few skills ({n_skills}). You MUST define at least 3 skills."
        if n_skills > 8:
            return f"Too many skills ({n_skills}). You MUST define at most 8 skills."
        
        # Check for unique skill IDs
        skill_ids = [s.get("skill_id") for s in skills]
        if len(skill_ids) != len(set(skill_ids)):
            return "Duplicate skill_id found"
        
        return None
