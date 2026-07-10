"""
Consensus-aware Taxonomist Stage.

Pipeline:
1. Read scaffold brief
2. Read structured transformation consensus
3. Inject both into Expert and Supervisor prompts
4. Use recommended_final_k from consensus when target_k_exact is not provided
5. Produce final codebook via existing Expert Committee + Supervisor workflow
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
from src.prompt_context import build_unified_context_text
from src.supervisor import SupervisorAlign, SupervisorConsolidate

JsonDict = Dict[str, Any]


def _augment_prompt(
    base_prompt: str,
    scaffold_brief: JsonDict | None,
    transform_consensus: JsonDict | None,
) -> str:
    if scaffold_brief and transform_consensus:
        context = build_unified_context_text(scaffold_brief, transform_consensus)
        return base_prompt + "\n\n---\n\n" + context
    return base_prompt


def run_expert(
    expert_id: str,
    verified_dossiers: List[JsonDict],
    prompts_dir: str,
    scaffold_brief: JsonDict | None,
    transform_consensus: JsonDict | None,
    target_k_exact: int | None = None,
    domain_guide: str | None = None,
) -> JsonDict:
    llm = LLMClient()
    raw_prompt = load_text(str(Path(prompts_dir) / "expert.txt"))
    prompt_text = _augment_prompt(raw_prompt, scaffold_brief, transform_consensus)
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
        description="Build a skill codebook using scaffold + transformation consensus."
    )
    parser.add_argument("--input", default="outputs/step2_verifier_verified_item_dossiers.jsonl", help="Verified dossiers JSONL")
    parser.add_argument("--scaffold_brief", default="outputs/step2_5_scaffold_brief.json", help="Scaffold brief JSON")
    parser.add_argument("--consensus", default="outputs/step2_7_transform_consensus.json", help="Transformation consensus JSON")
    parser.add_argument("--out", default="outputs/step3_skill_codebook_consensus.json", help="Output final codebook JSON")
    parser.add_argument("--out_experts", default="outputs/step3_expert_codebooks_consensus.json", help="Output individual expert codebooks")
    parser.add_argument("--out_align", default="outputs/step3_supervisor_align_output_consensus.json", help="Output supervisor alignment result")
    parser.add_argument("--out_supervisor", default="outputs/step3_supervisor_output_consensus.json", help="Output supervisor consolidation details")
    parser.add_argument("--parallel", action="store_true", default=True, help="Run experts in parallel (default: True)")
    parser.add_argument("--prompts_dir", default="prompts/v5_guided", help="Directory containing prompt files")
    parser.add_argument("--target_k_exact", type=int, default=None, help="Optional exact final K constraint.")
    parser.add_argument("--guides_dir", default=None, help="Directory containing guide txt files (optional)")
    args = parser.parse_args()

    load_dotenv(override=False)

    for path in [args.out, args.out_experts, args.out_align, args.out_supervisor]:
        ensure_dir(str(Path(path).parent))
        Path(path).unlink(missing_ok=True)

    verified = read_jsonl(args.input)
    scaffold_brief = read_json(args.scaffold_brief) if Path(args.scaffold_brief).exists() else None
    transform_consensus = read_json(args.consensus) if Path(args.consensus).exists() else None
    expert_ids = ["A", "B", "C"]

    expert_guide: str | None = None
    if args.guides_dir:
        expert_guide = load_guides(args.guides_dir, ["domain_core.txt", "skill_ontology_guide.txt"])

    effective_target_k = args.target_k_exact
    if effective_target_k is None and transform_consensus is not None:
        recommended_k = transform_consensus.get("recommended_final_k")
        if isinstance(recommended_k, int) and recommended_k > 0:
            effective_target_k = recommended_k

    print("=== Phase 1: Consensus-aware Expert Committee ===")
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
                    transform_consensus,
                    effective_target_k,
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
                transform_consensus,
                effective_target_k,
                expert_guide,
            )
            expert_results[result["expert_id"]] = result["codebook"]
            print(f"  ✓ Expert {eid} completed")

    write_json(args.out_experts, expert_results)

    print("\n=== Phase 2a: Supervisor Align ===")
    llm = LLMClient()
    aligner = SupervisorAlign(llm=llm, prompt_path=str(Path(args.prompts_dir) / "supervisor_align.txt"))
    alignment_output = aligner.align(
        codebook_a=expert_results["A"],
        codebook_b=expert_results["B"],
        codebook_c=expert_results["C"],
    )
    write_json(args.out_align, alignment_output)

    print("\n=== Phase 2b: Supervisor Consolidate ===")
    raw_consolidate = load_text(str(Path(args.prompts_dir) / "supervisor_consolidate.txt"))
    consolidate_prompt_text = _augment_prompt(raw_consolidate, scaffold_brief, transform_consensus)
    consolidator = SupervisorConsolidate(
        llm=llm,
        prompt_text=consolidate_prompt_text,
        target_k_exact=effective_target_k,
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
    print(f"Consensus-aware final codebook saved to: {args.out}")
    if effective_target_k is not None:
        print(f"Effective final K constraint: {effective_target_k}")


if __name__ == "__main__":
    main()
