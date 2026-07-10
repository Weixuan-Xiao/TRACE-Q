"""
Scaffold-aware Taxonomist Stage.

This runner preserves the current Expert Committee + Supervisor structure but
injects a shared scaffold brief into the expert and supervisor prompts. It is a
non-breaking alternative to `main_taxonomist.py` while the full refactor is in
progress.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from src.agent_utils import load_guides, load_text
from src.expert import Expert
from src.io_utils import ensure_dir, read_json, read_jsonl, write_json
from src.llm_client import LLMClient
from src.prompt_context import build_scaffold_only_context_text
from src.supervisor import SupervisorAlign, SupervisorConsolidate

JsonDict = Dict[str, Any]


def _prompt_with_scaffold(base_prompt: str, scaffold_brief: JsonDict | None) -> str:
    if not scaffold_brief:
        return base_prompt
    context = build_scaffold_only_context_text(scaffold_brief)
    return base_prompt + "\n\n---\n\n" + context


def run_expert(
    expert_id: str,
    verified_dossiers: List[JsonDict],
    prompts_dir: str,
    scaffold_brief: JsonDict | None,
    target_k_exact: int | None = None,
    domain_guide: str | None = None,
) -> JsonDict:
    llm = LLMClient()
    raw_prompt = load_text(str(Path(prompts_dir) / "expert.txt"))
    prompt_text = _prompt_with_scaffold(raw_prompt, scaffold_brief)
    expert = Expert(
        llm=llm,
        expert_id=expert_id,
        prompt_text=prompt_text,
        target_k_exact=target_k_exact,
        domain_guide=domain_guide,
    )
    codebook = expert.build_codebook(verified_dossiers=verified_dossiers)
    return {"expert_id": expert_id, "codebook": codebook}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a skill codebook using a shared scaffold brief."
    )
    parser.add_argument(
        "--input",
        default="outputs/step2_verifier_verified_item_dossiers.jsonl",
        help="Verified dossiers JSONL",
    )
    parser.add_argument(
        "--scaffold_brief",
        default="outputs/step2_5_scaffold_brief.json",
        help="Scaffold brief JSON",
    )
    parser.add_argument(
        "--out",
        default="outputs/step3_skill_codebook_scaffold.json",
        help="Output final codebook JSON",
    )
    parser.add_argument(
        "--out_experts",
        default="outputs/step3_expert_codebooks_scaffold.json",
        help="Output individual expert codebooks",
    )
    parser.add_argument(
        "--out_align",
        default="outputs/step3_supervisor_align_output_scaffold.json",
        help="Output supervisor alignment result",
    )
    parser.add_argument(
        "--out_supervisor",
        default="outputs/step3_supervisor_output_scaffold.json",
        help="Output supervisor consolidation details",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Run experts in parallel (default: True)",
    )
    parser.add_argument(
        "--prompts_dir",
        default="prompts/v5_guided",
        help="Directory containing prompt files",
    )
    parser.add_argument(
        "--target_k_exact",
        type=int,
        default=None,
        help="Optional exact final K constraint.",
    )
    parser.add_argument(
        "--guides_dir",
        default=None,
        help="Directory containing guide txt files (optional)",
    )
    args = parser.parse_args()

    load_dotenv(override=False)

    for path in [args.out, args.out_experts, args.out_align, args.out_supervisor]:
        ensure_dir(str(Path(path).parent))
        Path(path).unlink(missing_ok=True)

    verified = read_jsonl(args.input)
    scaffold_brief = read_json(args.scaffold_brief) if Path(args.scaffold_brief).exists() else None
    expert_ids = ["A", "B", "C"]

    expert_guide: str | None = None
    if args.guides_dir:
        expert_guide = load_guides(args.guides_dir, ["domain_core.txt", "skill_ontology_guide.txt"])

    print("=== Phase 1: Scaffold-aware Expert Committee ===")
    expert_results: Dict[str, JsonDict] = {}

    if args.parallel:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(
                    run_expert,
                    eid,
                    verified,
                    args.prompts_dir,
                    scaffold_brief,
                    args.target_k_exact,
                    expert_guide,
                ): eid
                for eid in expert_ids
            }
            for future in as_completed(futures):
                eid = futures[future]
                result = future.result()
                expert_results[result["expert_id"]] = result["codebook"]
                print(f"  ✓ Expert {eid} completed")
    else:
        for eid in expert_ids:
            result = run_expert(
                eid,
                verified,
                args.prompts_dir,
                scaffold_brief,
                args.target_k_exact,
                expert_guide,
            )
            expert_results[result["expert_id"]] = result["codebook"]
            print(f"  ✓ Expert {eid} completed")

    write_json(args.out_experts, expert_results)

    print("\n=== Phase 2a: Supervisor Align ===")
    llm = LLMClient()
    aligner = SupervisorAlign(
        llm=llm,
        prompt_path=str(Path(args.prompts_dir) / "supervisor_align.txt"),
    )
    alignment_output = aligner.align(
        codebook_a=expert_results["A"],
        codebook_b=expert_results["B"],
        codebook_c=expert_results["C"],
    )
    write_json(args.out_align, alignment_output)

    print("\n=== Phase 2b: Supervisor Consolidate ===")
    raw_consolidate = load_text(str(Path(args.prompts_dir) / "supervisor_consolidate.txt"))
    consolidate_prompt_text = _prompt_with_scaffold(raw_consolidate, scaffold_brief)
    consolidator = SupervisorConsolidate(
        llm=llm,
        prompt_text=consolidate_prompt_text,
        target_k_exact=args.target_k_exact,
        domain_guide=expert_guide,
    )
    supervisor_output = consolidator.consolidate(
        alignment=alignment_output,
        codebook_a=expert_results["A"],
        codebook_b=expert_results["B"],
        codebook_c=expert_results["C"],
        dossiers=verified,
    )
    write_json(args.out_supervisor, supervisor_output)

    final_codebook = supervisor_output.get("final_codebook", {})
    write_json(args.out, final_codebook)
    print(f"Scaffold-aware final codebook saved to: {args.out}")


if __name__ == "__main__":
    main()
