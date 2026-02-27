"""
Supervisor Agents for consolidating multiple expert codebooks.

Two-phase approach:
  1. SupervisorAlign: Identify semantically equivalent skills across experts,
     producing a standardized candidate skill list.
  2. SupervisorConsolidate: Merge/keep/remove candidates to produce final
     codebook (3-8 skills).

Prompt version is selected via prompt_path (e.g. prompts/v2/supervisor_align.txt).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from schemas.supervisor_align_output import SupervisorAlignOutput
from schemas.supervisor_output import SupervisorConsolidateOutput
from src.agent_utils import call_json_with_validation, load_text
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]


# ---------------------------------------------------------------------------
# Schema description texts (sent during JSON-repair retries)
# ---------------------------------------------------------------------------

ALIGN_SCHEMA_TEXT = """Return JSON with exactly:
{
  "candidate_skills": [
    {
      "canonical_id": "C01",
      "canonical_name": "...",
      "canonical_definition": "...",
      "expert_a_skill_ids": ["S01"],
      "expert_b_skill_ids": ["S01"],
      "expert_c_skill_ids": ["S02"],
      "consensus": "3/3",
      "alignment_notes": "..."
    }
  ],
  "alignment_summary": "..."
}
No extra keys. Every expert skill_id must appear in exactly one candidate.
"""

CONSOLIDATE_SCHEMA_TEXT = """Return JSON with exactly:
{
  "final_codebook": {
    "version": "v1",
    "domain": "...",
    "skills": [
      {
        "skill_id": "S01",
        "name": "...",
        "definition": "...",
        "inclusion_criteria": [...],
        "exclusion_criteria": [...],
        "examples": [{"item_id": "...", "step_ids": [...]}],
        "prerequisites": [...]
      }
    ]
  },
  "decisions": [
    {"action": "merge|keep|remove|rename|refine", "details": "...", "reasoning": "..."}
  ],
  "summary": "..."
}
The final_codebook MUST have exactly 3-8 skills. No extra keys.
"""

# ---------------------------------------------------------------------------
# Two-phase approach: SupervisorAlign + SupervisorConsolidate
# ---------------------------------------------------------------------------

class SupervisorAlign:
    """
    Phase 1: Align skills across expert codebooks.

    Identifies semantically equivalent skills and produces a standardized
    candidate skill list with consensus levels.
    """

    def __init__(
        self,
        llm: LLMClient,
        prompt_path: str | Path = "prompts/v2/supervisor_align.txt",
    ) -> None:
        self.llm = llm
        self.prompt_path = str(prompt_path)
        self._system_prompt = load_text(self.prompt_path)

    def align(
        self,
        *,
        codebook_a: JsonDict,
        codebook_b: JsonDict,
        codebook_c: JsonDict,
        max_fix_retries: int = 2,
    ) -> JsonDict:
        """
        Align three expert codebooks into a candidate skill list.

        Args:
            codebook_a: Codebook from Expert A
            codebook_b: Codebook from Expert B
            codebook_c: Codebook from Expert C
            max_fix_retries: Max retries for JSON repair

        Returns:
            SupervisorAlignOutput as dict
        """
        user_json = {
            "codebooks": {
                "A": codebook_a,
                "B": codebook_b,
                "C": codebook_c,
            },
        }

        return call_json_with_validation(
            llm=self.llm,
            system_prompt=self._system_prompt,
            user_json=user_json,
            model_cls=SupervisorAlignOutput,
            required_schema_text=ALIGN_SCHEMA_TEXT,
            extra_validator=lambda out: self._validate_alignment(
                out, codebook_a, codebook_b, codebook_c
            ),
            max_fix_retries=max_fix_retries,
        )

    def _validate_alignment(
        self,
        output: JsonDict,
        codebook_a: JsonDict,
        codebook_b: JsonDict,
        codebook_c: JsonDict,
    ) -> Optional[str]:
        """Validate that all expert skill_ids are covered in the alignment."""
        # Collect all expert skill IDs
        expert_ids: Dict[str, Set[str]] = {
            "A": {s.get("skill_id", "") for s in codebook_a.get("skills", [])},
            "B": {s.get("skill_id", "") for s in codebook_b.get("skills", [])},
            "C": {s.get("skill_id", "") for s in codebook_c.get("skills", [])},
        }

        # Collect mapped IDs from candidates
        mapped: Dict[str, Set[str]] = {"A": set(), "B": set(), "C": set()}
        for cand in output.get("candidate_skills", []):
            for sid in cand.get("expert_a_skill_ids", []):
                mapped["A"].add(sid)
            for sid in cand.get("expert_b_skill_ids", []):
                mapped["B"].add(sid)
            for sid in cand.get("expert_c_skill_ids", []):
                mapped["C"].add(sid)

        # Check coverage
        for expert_key in ["A", "B", "C"]:
            missing = expert_ids[expert_key] - mapped[expert_key]
            if missing:
                return (
                    f"Expert {expert_key} skill_ids not mapped: {sorted(missing)}. "
                    f"Every expert skill must appear in exactly one candidate."
                )

        # Validate consensus values
        for cand in output.get("candidate_skills", []):
            a_present = len(cand.get("expert_a_skill_ids", [])) > 0
            b_present = len(cand.get("expert_b_skill_ids", [])) > 0
            c_present = len(cand.get("expert_c_skill_ids", [])) > 0
            actual_count = sum([a_present, b_present, c_present])
            claimed = cand.get("consensus", "")
            expected = f"{actual_count}/3"
            if claimed != expected:
                return (
                    f"Candidate {cand.get('canonical_id')}: consensus claims "
                    f"{claimed} but expert presence is {expected}"
                )

        return None


class SupervisorConsolidate:
    """
    Phase 2: Consolidate aligned candidate skills into final codebook.

    Makes merge/keep/remove/refine decisions to produce a codebook with 3-8 skills.
    """

    def __init__(
        self,
        llm: LLMClient,
        prompt_path: str | Path | None = None,
        prompt_text: str | None = None,
        target_k_exact: int | None = None,
    ) -> None:
        self.llm = llm
        self.target_k_exact = target_k_exact
        if prompt_text is not None:
            self._system_prompt = prompt_text
        elif prompt_path is not None:
            self.prompt_path = str(prompt_path)
            self._system_prompt = load_text(self.prompt_path)
        else:
            raise ValueError("Either prompt_path or prompt_text must be provided")

    def consolidate(
        self,
        *,
        alignment: JsonDict,
        codebook_a: JsonDict,
        codebook_b: JsonDict,
        codebook_c: JsonDict,
        dossiers: List[JsonDict],
        max_fix_retries: int = 2,
    ) -> JsonDict:
        """
        Consolidate aligned candidates into a final codebook.

        Args:
            alignment: Output from SupervisorAlign.align()
            codebook_a: Codebook from Expert A (for reference)
            codebook_b: Codebook from Expert B
            codebook_c: Codebook from Expert C
            dossiers: Original verified dossiers for reference
            max_fix_retries: Max retries for JSON repair

        Returns:
            SupervisorConsolidateOutput as dict
        """
        dossiers_summary = self._summarize_dossiers(dossiers)

        user_json = {
            "alignment": alignment,
            "codebooks": {
                "A": codebook_a,
                "B": codebook_b,
                "C": codebook_c,
            },
            "dossiers_summary": dossiers_summary,
        }

        return call_json_with_validation(
            llm=self.llm,
            system_prompt=self._system_prompt,
            user_json=user_json,
            model_cls=SupervisorConsolidateOutput,
            required_schema_text=CONSOLIDATE_SCHEMA_TEXT,
            extra_validator=self._validate_skill_count,
            max_fix_retries=max_fix_retries,
        )

    def _summarize_dossiers(self, dossiers: List[JsonDict]) -> List[JsonDict]:
        """Create a compact summary of dossiers."""
        summaries: List[JsonDict] = []
        for d in dossiers:
            item = d.get("item", {})
            solver = d.get("solver", {})

            stem_text = str(item.get("stem_text", ""))
            if len(stem_text) > 200:
                stem_text = stem_text[:200] + "..."

            summaries.append({
                "item_id": str(d.get("item_id", item.get("item_id", ""))).strip(),
                "stem_text": stem_text,
                "solution_steps": solver.get("solution_steps", []),
            })

        return summaries

    def _validate_skill_count(self, output: JsonDict) -> Optional[str]:
        """Validate that final codebook has the correct number of skills."""
        final_codebook = output.get("final_codebook", {})
        skills = final_codebook.get("skills", [])
        n_skills = len(skills)

        if self.target_k_exact:
            if n_skills != self.target_k_exact:
                return f"Expected exactly {self.target_k_exact} skills, got {n_skills}."
        else:
            if n_skills < 3:
                return f"Too few skills ({n_skills}). Final codebook MUST have at least 3 skills."
            if n_skills > 8:
                return f"Too many skills ({n_skills}). Final codebook MUST have at most 8 skills."

        # Check for unique skill IDs
        skill_ids = [s.get("skill_id") for s in skills]
        if len(skill_ids) != len(set(skill_ids)):
            return "Duplicate skill_id found in final_codebook"

        return None
