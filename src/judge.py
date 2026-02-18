"""
Judge Agent: Adjudicates tagger votes to produce final skill assignments.

Works with both flat and hierarchical codebooks.
Supports skill-level voting context via optional vote_stats parameter.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Set

from schemas.judge_output import JudgeOutput
from src.agent_utils import call_json_with_validation, load_text
from src.codebook_utils import extract_skill_ids, codebook_to_flat_format
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]


JUDGE_SCHEMA_TEXT = """Return JSON with exactly:
{
  "final_skills":[{"skill_id":"S01","evidence_step_ids":["Step2"],"confidence":0.0-1.0}, ...],
  "judge_notes":"..."
}
Rules:
- skill_id must exist in codebook
- evidence_step_ids must be existing step_id values from dossier.solver.solution_steps
"""


def _extract_step_ids(dossier: JsonDict) -> Set[str]:
    steps = dossier.get("solver", {}).get("solution_steps", [])
    return {str(s.get("step_id")).strip() for s in steps if str(s.get("step_id", "")).strip()}


class Judge:
    """Judge agent for vote adjudication."""

    def __init__(
        self,
        llm: LLMClient,
        prompt_path: str | Path = "prompts/v2/judge.txt",
    ) -> None:
        self.llm = llm
        self.prompt_path = str(prompt_path)
        self._system_prompt = load_text(self.prompt_path)

    def adjudicate(
        self,
        *,
        codebook: JsonDict,
        dossier: JsonDict,
        votes: JsonDict,
        vote_stats: Optional[JsonDict] = None,
        max_fix_retries: int = 2,
    ) -> JsonDict:
        """
        Adjudicate tagger votes to determine final skill assignments.

        Args:
            codebook: Skill codebook (flat or hierarchical)
            dossier: Item dossier with solution steps
            votes: Dict of tagger votes {tagger_id: vote}
            vote_stats: Optional skill-level voting statistics with keys:
                - skill_counts: {skill_id: count}
                - auto_include: [skill_ids with >=4/5 agreement]
                - auto_exclude: [skill_ids with <=1/5 agreement]
                - disputed: [skill_ids with 2/5 or 3/5 agreement]
            max_fix_retries: Max retries for JSON repair

        Returns:
            JudgeOutput as dict
        """
        # Convert hierarchical to flat for validation and sending to LLM
        flat_codebook = codebook_to_flat_format(codebook)

        allowed_step_ids = _extract_step_ids(dossier)
        allowed_skill_ids = extract_skill_ids(codebook)

        def extra_validate(out: JsonDict) -> Optional[str]:
            for s in out.get("final_skills", []):
                sid = str(s.get("skill_id", "")).strip()
                if sid not in allowed_skill_ids:
                    return f"Unknown skill_id in final_skills: {sid}"
                for eid in s.get("evidence_step_ids", []):
                    e = str(eid).strip()
                    if e not in allowed_step_ids:
                        return f"Unknown evidence_step_id: {e}. Allowed: {sorted(list(allowed_step_ids))}"
            return None

        user_json: JsonDict = {
            "codebook": flat_codebook,
            "dossier": dossier,
            "votes": votes,
            "constraints": {
                "allowed_step_ids": sorted(list(allowed_step_ids)),
                "allowed_skill_ids": sorted(list(allowed_skill_ids)),
            },
        }

        # Include skill-level voting stats if provided
        if vote_stats is not None:
            user_json["vote_stats"] = vote_stats

        return call_json_with_validation(
            llm=self.llm,
            system_prompt=self._system_prompt,
            user_json=user_json,
            model_cls=JudgeOutput,
            required_schema_text=JUDGE_SCHEMA_TEXT,
            extra_validator=extra_validate,
            max_fix_retries=max_fix_retries,
        )
