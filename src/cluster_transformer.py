from __future__ import annotations

from typing import Any, Dict, List

from schemas.cluster_transform import ClusterTransformOutput
from src.agent_utils import call_json_with_validation
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]

_TRANSFORM_SCHEMA = """Return JSON with exactly:
{
  "version": "v1",
  "expert_id": "A|B|C",
  "decisions": [
    {
      "cluster_id": "C01",
      "action": "keep|merge|split|relabel",
      "target_cluster_ids": ["C02"],
      "proposed_skill_names": ["..."],
      "reasoning": "..."
    }
  ],
  "draft_skills": [
    {
      "provisional_skill_id": "DS01",
      "name": "...",
      "definition": "...",
      "source_cluster_ids": ["C01"],
      "inclusion_criteria": ["..."],
      "exclusion_criteria": ["..."]
    }
  ],
  "summary": "..."
}
No extra keys. Every scaffold cluster_id must appear exactly once in decisions.
"""

_TRANSFORM_SYSTEM_PROMPT = """You are a cognitive-diagnostic ontology reviewer.
Your task is NOT to build the final codebook yet.
Instead, inspect a shared scaffold of clusters and decide, for each cluster, whether it should be kept, merged, split, or relabeled when inducing the final skill list.
Follow these principles:
- prefer mechanisms over surface topics
- avoid redundant skills
- preserve boundary clarity
- allow K_cluster to differ from final K_skill
- use keep / merge / split / relabel only when justified
Return strict JSON only.
"""


class ClusterTransformer:
    def __init__(self, llm: LLMClient, expert_id: str) -> None:
        self.llm = llm
        self.expert_id = expert_id

    def transform(
        self,
        *,
        scaffold_brief: JsonDict,
        dossiers_summary: List[JsonDict],
        max_fix_retries: int = 2,
    ) -> JsonDict:
        user_json = {
            "expert_id": self.expert_id,
            "scaffold_brief": scaffold_brief,
            "dossiers_summary": dossiers_summary,
        }
        return call_json_with_validation(
            llm=self.llm,
            system_prompt=_TRANSFORM_SYSTEM_PROMPT,
            user_json=user_json,
            model_cls=ClusterTransformOutput,
            required_schema_text=_TRANSFORM_SCHEMA,
            extra_validator=lambda out: self._validate_output(out, scaffold_brief),
            max_fix_retries=max_fix_retries,
        )

    def _validate_output(self, out: JsonDict, scaffold_brief: JsonDict) -> str | None:
        expected = {cluster.get("cluster_id", "") for cluster in scaffold_brief.get("clusters", [])}
        seen = [decision.get("cluster_id", "") for decision in out.get("decisions", [])]
        seen_set = set(seen)
        if expected != seen_set:
            missing = sorted(expected - seen_set)
            extra = sorted(seen_set - expected)
            return f"Decision coverage mismatch. Missing={missing}; Extra={extra}"
        if len(seen) != len(seen_set):
            return "Duplicate cluster_id found in decisions"
        return None


def summarize_dossiers_for_transform(dossiers: List[JsonDict]) -> List[JsonDict]:
    summaries: List[JsonDict] = []
    for d in dossiers:
        item = d.get("item", {}) if isinstance(d.get("item"), dict) else {}
        solver = d.get("solver", {}) if isinstance(d.get("solver"), dict) else {}
        stem_text = str(item.get("stem_text", item.get("question", "")))
        step_texts = solver.get("solution_steps", []) if isinstance(solver.get("solution_steps", []), list) else []
        compact_steps = []
        for step in step_texts[:3]:
            if isinstance(step, str):
                compact_steps.append(step[:120])
            elif isinstance(step, dict):
                text = str(step.get("text", step.get("description", "")))
                if text:
                    compact_steps.append(text[:120])
        summaries.append(
            {
                "item_id": str(d.get("item_id", item.get("item_id", ""))).strip(),
                "stem_text": stem_text[:200],
                "solution_steps": compact_steps,
            }
        )
    return summaries


def transformations_to_prompt_text(transform_outputs: List[JsonDict]) -> str:
    lines: List[str] = []
    lines.append("CLUSTER TRANSFORMATION REVIEW")
    for output in transform_outputs:
        eid = output.get("expert_id", "?")
        lines.append(f"Expert {eid} decisions:")
        for decision in output.get("decisions", []):
            cid = decision.get("cluster_id", "?")
            action = decision.get("action", "?")
            targets = ", ".join(decision.get("target_cluster_ids", []))
            names = ", ".join(decision.get("proposed_skill_names", []))
            lines.append(f"- {cid}: {action}")
            if targets:
                lines.append(f"  targets: {targets}")
            if names:
                lines.append(f"  names: {names}")
    return "\n".join(lines)
