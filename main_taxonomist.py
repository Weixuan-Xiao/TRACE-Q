"""
Taxonomist Stage: Build flat skill codebook using Expert Committee + Supervisor.

1. Three Experts independently generate codebooks (K=3-8 each)
2. Supervisor_Align aligns skills across experts into a standardized candidate list
3. Supervisor_Consolidate merges/keeps/removes to produce final codebook (K=3-8)

Prompt version is selected via --prompts_dir (e.g. prompts/v1, prompts/v2).
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from src.agent_utils import load_text
from src.expert import Expert
from src.io_utils import ensure_dir, read_jsonl, write_json
from src.llm_client import LLMClient
from src.supervisor import SupervisorAlign, SupervisorConsolidate

JsonDict = Dict[str, Any]


def run_expert(
    expert_id: str,
    verified_dossiers: List[JsonDict],
    prompts_dir: str,
    prompt_text: str | None = None,
) -> JsonDict:
    """
    Run a single Expert to generate a codebook.
    Each Expert creates its own LLMClient to avoid thread-safety issues.
    """
    llm = LLMClient()
    if prompt_text is not None:
        expert = Expert(llm=llm, expert_id=expert_id, prompt_text=prompt_text)
    else:
        expert = Expert(
            llm=llm,
            expert_id=expert_id,
            prompt_path=str(Path(prompts_dir) / "expert.txt"),
        )
    codebook = expert.build_codebook(verified_dossiers=verified_dossiers)
    return {"expert_id": expert_id, "codebook": codebook}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build skill codebook using Expert Committee + Supervisor."
    )
    parser.add_argument(
        "--input",
        default="outputs/step2_verifier_verified_item_dossiers.jsonl",
        help="Verified dossiers JSONL",
    )
    parser.add_argument(
        "--out",
        default="outputs/step3_skill_codebook.json",
        help="Output final codebook JSON",
    )
    parser.add_argument(
        "--out_experts",
        default="outputs/step3_expert_codebooks.json",
        help="Output individual expert codebooks",
    )
    parser.add_argument(
        "--out_align",
        default="outputs/step3_supervisor_align_output.json",
        help="Output supervisor alignment result (two-phase only)",
    )
    parser.add_argument(
        "--out_supervisor",
        default="outputs/step3_supervisor_output.json",
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
        default="prompts/v2",
        help="Directory containing prompt files",
    )
    parser.add_argument(
        "--target_k_exact", type=int, default=None,
        help="Constrain experts to produce exactly this many skills.",
    )
    args = parser.parse_args()

    load_dotenv(override=False)

    # Ensure output dirs exist
    for path in [args.out, args.out_experts, args.out_align, args.out_supervisor]:
        ensure_dir(str(Path(path).parent))

    # Clean up old outputs
    for path in [args.out, args.out_experts, args.out_align, args.out_supervisor]:
        Path(path).unlink(missing_ok=True)

    verified = read_jsonl(args.input)
    expert_ids = ["A", "B", "C"]

    # Prepare prompt text override when --target_k_exact is set
    expert_prompt_text = None
    if args.target_k_exact:
        k = args.target_k_exact
        expert_prompt_text = load_text(str(Path(args.prompts_dir) / "expert.txt"))
        expert_prompt_text = expert_prompt_text.replace(
            "between 3 and 8 skills (inclusive)",
            f"exactly {k} skills"
        ).replace(
            "No fewer than 3, no more than 8",
            f"Exactly {k} — no more, no fewer"
        ).replace(
            "You MUST define between 3 and 8 skills",
            f"You MUST define exactly {k} skills"
        )

    # === Phase 1: Three Experts generate codebooks ===
    print("=== Phase 1: Expert Committee generating codebooks (K=3-8) ===")

    expert_results: Dict[str, JsonDict] = {}

    if args.parallel:
        print(f"Running {len(expert_ids)} experts in parallel...")
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(run_expert, eid, verified, args.prompts_dir, expert_prompt_text): eid
                for eid in expert_ids
            }

            for future in as_completed(futures):
                eid = futures[future]
                try:
                    result = future.result()
                    expert_results[result["expert_id"]] = result["codebook"]
                    n_skills = len(result["codebook"].get("skills", []))
                    print(f"  ✓ Expert {eid} completed: {n_skills} skills")
                except Exception as e:
                    print(f"  ✗ Expert {eid} failed: {e}")
                    raise
    else:
        for eid in expert_ids:
            print(f"Running Expert {eid}...")
            result = run_expert(eid, verified, args.prompts_dir, expert_prompt_text)
            expert_results[result["expert_id"]] = result["codebook"]
            n_skills = len(result["codebook"].get("skills", []))
            print(f"  ✓ Expert {eid} completed: {n_skills} skills")

    write_json(args.out_experts, expert_results)
    print(f"Expert codebooks saved to: {args.out_experts}")

    # === Phase 2a: Supervisor Align ===
    print("\n=== Phase 2a: Supervisor Align (standardizing skill names) ===")

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
    n_candidates = len(alignment_output.get("candidate_skills", []))
    print(f"  ✓ Alignment complete: {n_candidates} candidate skills identified")
    print(f"  Alignment output saved to: {args.out_align}")

    # Print candidate summary
    for cand in alignment_output.get("candidate_skills", []):
        cid = cand.get("canonical_id", "?")
        name = cand.get("canonical_name", "?")
        consensus = cand.get("consensus", "?")
        print(f"    {cid}: {name} (consensus: {consensus})")

    # === Phase 2b: Supervisor Consolidate ===
    print("\n=== Phase 2b: Supervisor Consolidate (final codebook) ===")

    consolidate_kwargs: Dict[str, Any] = {"llm": llm}
    if args.target_k_exact:
        consolidate_prompt_text = load_text(str(Path(args.prompts_dir) / "supervisor_consolidate.txt"))
        consolidate_prompt_text = consolidate_prompt_text.replace(
            "3-8 skills", f"exactly {args.target_k_exact} skills"
        ).replace(
            "MUST have exactly 3-8 skills", f"MUST have exactly {args.target_k_exact} skills"
        )
        consolidate_kwargs["prompt_text"] = consolidate_prompt_text
        consolidate_kwargs["target_k_exact"] = args.target_k_exact
    else:
        consolidate_kwargs["prompt_path"] = str(Path(args.prompts_dir) / "supervisor_consolidate.txt")

    consolidator = SupervisorConsolidate(**consolidate_kwargs)

    supervisor_output = consolidator.consolidate(
        alignment=alignment_output,
        codebook_a=expert_results["A"],
        codebook_b=expert_results["B"],
        codebook_c=expert_results["C"],
        dossiers=verified,
    )

    write_json(args.out_supervisor, supervisor_output)
    print(f"Supervisor output saved to: {args.out_supervisor}")

    # Extract and save final codebook
    final_codebook = supervisor_output.get("final_codebook", {})
    write_json(args.out, final_codebook)

    n_final_skills = len(final_codebook.get("skills", []))
    print(f"\nFinal codebook saved to: {args.out}")
    print(f"Total skills (K): {n_final_skills}")

    # Print summary
    summary = supervisor_output.get("summary", "")
    if summary:
        print(f"\nSupervisor summary: {summary}")

    # Print skill list
    print("\nFinal skills:")
    for skill in final_codebook.get("skills", []):
        sid = skill.get("skill_id", "?")
        name = skill.get("name", "?")
        print(f"  {sid}: {name}")


if __name__ == "__main__":
    main()
