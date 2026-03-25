"""
Tagger Agent: Tags items with skills from the codebook.

Works with both flat and hierarchical codebooks.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Set

from schemas.tagger_vote import TaggerVote
from src.agent_utils import call_json_with_validation, load_text
from src.codebook_utils import extract_skill_ids, codebook_to_flat_format
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]


TAGGER_SCHEMA_TEXT = """Return JSON with exactly:
{
  "skills":[{"skill_id":"S01","evidence_step_ids":["Step2"],"reasoning":"Why this skill is necessary"}, ...],
  "optional_skills":[{"skill_id":"Sxx","reason":"..."}, ...]
}
Rules:
- skill_id must exist in codebook
- evidence_step_ids must be existing step_id values from dossier.solver.solution_steps
- reasoning must explain why this skill is essential for solving the problem
"""


def _extract_step_ids(dossier: JsonDict) -> Set[str]:
    steps = dossier.get("solver", {}).get("solution_steps", [])
    return {str(s.get("step_id")).strip() for s in steps if str(s.get("step_id", "")).strip()}


class Tagger:
    """Tagger agent for skill annotation."""

    def __init__(
        self,
        llm: LLMClient,
        *,
        tagger_id: str,
        prompt_path: str | Path = "prompts/v2/tagger.txt",
        domain_guide: str | None = None,
    ) -> None:
        self.llm = llm
        self.tagger_id = tagger_id
        self.prompt_path = str(prompt_path)
        base_prompt = load_text(self.prompt_path)
        preamble = f'You are Tagger "{self.tagger_id}".'
        if domain_guide:
            self._system_prompt = preamble + "\n\n" + domain_guide + "\n\n---\n\n" + base_prompt
        else:
            self._system_prompt = preamble + "\n\n" + base_prompt

    def tag(
        self,
        *,
        codebook: JsonDict,
        dossier: JsonDict,
        max_fix_retries: int = 2,
    ) -> JsonDict:
        """
        Tag an item with skills from the codebook.
        
        Args:
            codebook: Skill codebook (flat or hierarchical)
            dossier: Item dossier with solution steps
            max_fix_retries: Max retries for JSON repair
            
        Returns:
            TaggerVote as dict
        """
        # Convert hierarchical to flat for validation and sending to LLM
        flat_codebook = codebook_to_flat_format(codebook)
        
        allowed_step_ids = _extract_step_ids(dossier)
        allowed_skill_ids = extract_skill_ids(codebook)

        def extra_validate(vote: JsonDict) -> Optional[str]:
            for s in vote.get("skills", []):
                sid = str(s.get("skill_id", "")).strip()
                if sid not in allowed_skill_ids:
                    return f"Unknown skill_id in skills: {sid}"
                for eid in s.get("evidence_step_ids", []):
                    e = str(eid).strip()
                    if e not in allowed_step_ids:
                        return f"Unknown evidence_step_id: {e}. Allowed: {sorted(list(allowed_step_ids))}"
            for s in vote.get("optional_skills", []):
                sid = str(s.get("skill_id", "")).strip()
                if sid and sid not in allowed_skill_ids:
                    return f"Unknown skill_id in optional_skills: {sid}"
            return None

        user_json = {
            "codebook": flat_codebook,
            "dossier": dossier,
            "constraints": {
                "allowed_step_ids": sorted(list(allowed_step_ids)),
                "allowed_skill_ids": sorted(list(allowed_skill_ids)),
            },
        }
        
        return call_json_with_validation(
            llm=self.llm,
            system_prompt=self._system_prompt,
            user_json=user_json,
            model_cls=TaggerVote,
            required_schema_text=TAGGER_SCHEMA_TEXT,
            extra_validator=extra_validate,
            max_fix_retries=max_fix_retries,
        )
