"""
Expert Agent: Domain expert for skill codebook generation.

Multiple Expert instances run in parallel to generate independent flat codebooks.
When ``target_k_exact`` is set the Expert is constrained to produce exactly that
many skills; otherwise the default range 3-8 applies.
These codebooks are then consolidated by the Supervisor.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from schemas.codebook import Codebook
from src.agent_utils import call_json_with_validation, load_text
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]

_EXPERT_SCHEMA_TEMPLATE = """Return JSON with exactly:
{{
  "version": "v1",
  "domain": "<string>",
  "skills": [
    {{
      "skill_id": "S01",
      "name": "...",
      "definition": "...",
      "inclusion_criteria": [...],
      "exclusion_criteria": [...],
      "examples": [{{"item_id": "...", "step_ids": ["..."]}}],
      "prerequisites": [...]
    }}
  ]
}}
No extra keys. You MUST define exactly {constraint} skills.
"""


def _build_schema_text(target_k_exact: int | None) -> str:
    constraint = str(target_k_exact) if target_k_exact else "3-8"
    return _EXPERT_SCHEMA_TEMPLATE.format(constraint=constraint)


class Expert:
    """Expert Agent for flat skill codebook generation."""

    def __init__(
        self,
        llm: LLMClient,
        expert_id: str = "A",
        prompt_path: str | Path | None = None,
        prompt_text: str | None = None,
        target_k_exact: int | None = None,
    ) -> None:
        self.llm = llm
        self.expert_id = expert_id
        self.target_k_exact = target_k_exact
        if prompt_text is not None:
            base_prompt = prompt_text
        elif prompt_path is not None:
            base_prompt = load_text(prompt_path)
        else:
            raise ValueError("Either prompt_path or prompt_text must be provided")
        self.prompt_path = str(prompt_path) if prompt_path else None
        self._system_prompt = base_prompt
        self._schema_text = _build_schema_text(target_k_exact)

    def build_codebook(
        self,
        *,
        verified_dossiers: List[JsonDict],
        max_fix_retries: int = 2,
    ) -> JsonDict:
        """Generate a flat skill codebook from verified dossiers."""
        user_json = {"verified_dossiers": verified_dossiers}

        codebook = call_json_with_validation(
            llm=self.llm,
            system_prompt=self._system_prompt,
            user_json=user_json,
            model_cls=Codebook,
            required_schema_text=self._schema_text,
            extra_validator=self._validate_skill_count,
            max_fix_retries=max_fix_retries,
        )

        if "version" not in codebook:
            codebook["version"] = "v1"

        return codebook

    def _validate_skill_count(self, codebook: JsonDict) -> Optional[str]:
        """Validate skill count against target_k_exact or the default 3-8 range."""
        skills = codebook.get("skills", [])
        n_skills = len(skills)

        if self.target_k_exact is not None:
            if n_skills != self.target_k_exact:
                return (
                    f"Expected exactly {self.target_k_exact} skills, got {n_skills}."
                )
        else:
            if n_skills < 3:
                return f"Too few skills ({n_skills}). You MUST define at least 3 skills."
            if n_skills > 8:
                return f"Too many skills ({n_skills}). You MUST define at most 8 skills."

        skill_ids = [s.get("skill_id") for s in skills]
        if len(skill_ids) != len(set(skill_ids)):
            return "Duplicate skill_id found"

        return None
