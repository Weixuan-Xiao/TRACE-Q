from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List


def _run(cmd: List[str], cwd: Path) -> None:
    print("\n>>>", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the end-to-end consensus pipeline: structure discovery -> cluster transformation -> "
            "transform consensus -> consensus-aware taxonomist -> optional taggers -> Q aggregation."
        )
    )
    parser.add_argument("--dossiers", default="outputs/step2_verifier_verified_item_dossiers.jsonl", help="Verified dossiers JSONL")
    parser.add_argument("--prompts_dir", default="prompts/v5_guided", help="Prompt directory for taxonomist stages")
    parser.add_argument("--guides_dir", default=None, help="Optional guides directory")
    parser.add_argument("--domain", default=None, help="Optional domain override for structure discovery")
    parser.add_argument("--min_k", type=int, default=3, help="Minimum candidate K for structure discovery")
    parser.add_argument("--max_k", type=int, default=8, help="Maximum candidate K for structure discovery")
    parser.add_argument("--target_k_cluster", type=int, default=None, help="Optional fixed K override for selected scaffold clusters")
    parser.add_argument("--target_k_skill", type=int, default=None, help="Optional exact final K constraint for taxonomist")
    parser.add_argument("--embedding_model", default=None, help="Optional embedding model override")
    parser.add_argument("--force_structure_method", choices=["auto", "embedding", "tfidf"], default="auto", help="Force structure discovery backend")
    parser.add_argument("--fallback_structure_method", choices=["none", "tfidf"], default="tfidf", help="Fallback backend if embeddings fail")
    parser.add_argument("--run_taggers", action="store_true", help="Run taggers after final codebook generation")
    parser.add_argument("--tagger_prompts_dir", default="prompts/v5_guided", help="Prompt directory for taggers")
    parser.add_argument("--n_taggers", type=int, default=5, help="Number of taggers if --run_taggers is set")
    parser.add_argument("--aggregate_q", action="store_true", help="Run Q aggregation after taggers")
    parser.add_argument("--decision_threshold", type=float, default=0.5, help="Vote threshold for Q aggregation")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    py = sys.executable

    structure_cmd = [
        py, "main_structure_discovery_embed.py",
        "--input", args.dossiers,
        "--out_cards", "outputs/step2_5_reasoning_cards.jsonl",
        "--out_candidates", "outputs/step2_5_cluster_candidates.json",
        "--out_scaffold", "outputs/step2_5_scaffold_brief.json",
        "--min_k", str(args.min_k),
        "--max_k", str(args.max_k),
        "--force_method", args.force_structure_method,
        "--fallback_method", args.fallback_structure_method,
    ]
    if args.domain:
        structure_cmd += ["--domain", args.domain]
    if args.target_k_cluster is not None:
        structure_cmd += ["--target_k", str(args.target_k_cluster)]
    if args.embedding_model:
        structure_cmd += ["--embedding_model", args.embedding_model]
    _run(structure_cmd, repo_root)

    transform_cmd = [
        py, "main_cluster_transform.py",
        "--input", args.dossiers,
        "--scaffold_brief", "outputs/step2_5_scaffold_brief.json",
        "--out", "outputs/step2_6_cluster_transformations.json",
    ]
    _run(transform_cmd, repo_root)

    consensus_cmd = [
        py, "main_transform_consensus.py",
        "--scaffold_brief", "outputs/step2_5_scaffold_brief.json",
        "--transformations", "outputs/step2_6_cluster_transformations.json",
        "--out", "outputs/step2_7_transform_consensus.json",
    ]
    _run(consensus_cmd, repo_root)

    taxonomist_cmd = [
        py, "main_taxonomist_consensus.py",
        "--input", args.dossiers,
        "--scaffold_brief", "outputs/step2_5_scaffold_brief.json",
        "--consensus", "outputs/step2_7_transform_consensus.json",
        "--out", "outputs/step3_skill_codebook_consensus.json",
        "--out_experts", "outputs/step3_expert_codebooks_consensus.json",
        "--out_align", "outputs/step3_supervisor_align_output_consensus.json",
        "--out_supervisor", "outputs/step3_supervisor_output_consensus.json",
        "--prompts_dir", args.prompts_dir,
    ]
    if args.guides_dir:
        taxonomist_cmd += ["--guides_dir", args.guides_dir]
    if args.target_k_skill is not None:
        taxonomist_cmd += ["--target_k_exact", str(args.target_k_skill)]
    _run(taxonomist_cmd, repo_root)

    if args.run_taggers:
        tagger_cmd = [
            py, "main_taggers.py",
            "--dossiers", args.dossiers,
            "--codebook", "outputs/step3_skill_codebook_consensus.json",
            "--out_dir", "outputs/step4_tagger_votes_consensus",
            "--prompts_dir", args.tagger_prompts_dir,
            "--n_taggers", str(args.n_taggers),
            "--parallel",
        ]
        _run(tagger_cmd, repo_root)

        if args.aggregate_q:
            agg_cmd = [
                py, "main_q_aggregate.py",
                "--votes_dir", "outputs/step4_tagger_votes_consensus",
                "--codebook", "outputs/step3_skill_codebook_consensus.json",
                "--out_q", "outputs/step5_final_q_matrix_consensus.jsonl",
                "--out_cells", "outputs/step5_cell_uncertainty_consensus.jsonl",
                "--out_items", "outputs/step5_item_uncertainty_consensus.jsonl",
                "--out_summary", "outputs/step5_stability_summary_consensus.json",
                "--decision_threshold", str(args.decision_threshold),
            ]
            _run(agg_cmd, repo_root)

    print("\nConsensus pipeline complete.")
    print("Final codebook: outputs/step3_skill_codebook_consensus.json")
    if args.run_taggers:
        print("Tagger votes: outputs/step4_tagger_votes_consensus/")
    if args.run_taggers and args.aggregate_q:
        print("Final Q-matrix: outputs/step5_final_q_matrix_consensus.jsonl")
        print("Stability summary: outputs/step5_stability_summary_consensus.json")


if __name__ == "__main__":
    main()
