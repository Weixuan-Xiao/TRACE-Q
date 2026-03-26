"""Auditor agent: reviews the final Q-matrix for correctness."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from schemas.auditor_output import AuditorOutput
from src.agent_utils import call_json_with_validation, load_text
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]

AUDITOR_SCHEMA_TEXT = """Return JSON with exactly:
{
  "item_id": "...",
  "auditor_skills": ["S01", "S04"],  // or ["M01", "M02"] for aggregated codebooks
  "verdict": "correct" | "error" | "controversial",
  "controversy_flags": [],
  "corrections": {
    "add_skills": [],
    "remove_skills": [],
    "reasoning": "..."
  }
}
No extra keys. verdict must be one of: correct, error, controversial.
Use the skill IDs exactly as they appear in the codebook (S## for original, M## for merged).
"""


class Auditor:
    """Reviews Q-matrix entries for correctness and flags controversial items."""

    def __init__(
        self,
        llm: LLMClient,
        *,
        prompt_path: str | Path = "prompts/v1/auditor.txt",
    ) -> None:
        self.llm = llm
        self.prompt_path = str(prompt_path)
        self._system_prompt = load_text(self.prompt_path).strip()

    def audit_item(
        self,
        *,
        item_id: str,
        stem_text: str,
        solution_steps: List[JsonDict],
        codebook: JsonDict,
        current_skills: List[str],
        tagger_agreement: str,
        full_agree: bool,
        max_fix_retries: int = 2,
    ) -> JsonDict:
        """
        Audit a single item's skill annotations.

        Args:
            item_id: The item identifier.
            stem_text: The problem statement.
            solution_steps: List of solution steps from verified dossier.
            codebook: The skill codebook with definitions.
            current_skills: List of skill IDs currently marked as 1 in Q-matrix.
            tagger_agreement: String describing tagger agreement (e.g., "5/5", "4/5").
            full_agree: Whether all 5 taggers fully agreed.
            max_fix_retries: Max retries for JSON repair.

        Returns:
            AuditorOutput as a dict.
        """
        # Prepare codebook summary for the prompt
        skills_summary = self._format_codebook_for_prompt(codebook)

        user_json = {
            "item_id": item_id,
            "stem_text": stem_text,
            "solution_steps": solution_steps,
            "skill_codebook": skills_summary,
            "current_skills": current_skills,
            "tagger_agreement": tagger_agreement,
            "tagger_full_agree": full_agree,
        }

        def extra_validate(output: JsonDict) -> Optional[str]:
            # Ensure item_id matches
            if output.get("item_id") != item_id:
                return f"item_id mismatch: expected {item_id}, got {output.get('item_id')}"
            # Ensure auditor_skills are valid skill IDs
            valid_skill_ids = self._get_valid_skill_ids(codebook)
            for sid in output.get("auditor_skills", []):
                if sid not in valid_skill_ids:
                    return f"Invalid skill_id in auditor_skills: {sid}"
            return None

        return call_json_with_validation(
            llm=self.llm,
            system_prompt=self._system_prompt,
            user_json=user_json,
            model_cls=AuditorOutput,
            required_schema_text=AUDITOR_SCHEMA_TEXT,
            extra_validator=extra_validate,
            max_fix_retries=max_fix_retries,
        )

    def _format_codebook_for_prompt(self, codebook: JsonDict) -> List[JsonDict]:
        """Format codebook skills for inclusion in the prompt.
        
        Handles both original (skill_id) and aggregated (merged_id) codebooks.
        """
        skills = codebook.get("skills", [])
        formatted = []
        for s in skills:
            # Handle both original and merged formats
            skill_id = s.get("skill_id") or s.get("merged_id", "")
            formatted.append({
                "skill_id": skill_id,
                "name": s.get("name", ""),
                "definition": s.get("definition", ""),
                "inclusion_criteria": s.get("inclusion_criteria", []),
                "exclusion_criteria": s.get("exclusion_criteria", []),
                # Include merge info if available (for aggregated codebooks)
                "original_skill_ids": s.get("original_skill_ids", []),
            })
        return formatted

    def _get_valid_skill_ids(self, codebook: JsonDict) -> Set[str]:
        """Extract valid skill IDs from codebook.
        
        Handles both original (skill_id) and aggregated (merged_id) codebooks.
        """
        skills = codebook.get("skills", [])
        valid_ids = set()
        for s in skills:
            sid = s.get("skill_id") or s.get("merged_id", "")
            if sid:
                valid_ids.add(sid)
        return valid_ids

