"""
Aggregator Stage: Create multiple K-level codebooks by merging skills.

Takes the fine-grained codebook (K_max=3-8) and creates coarser versions
(e.g., K=6, K=5, K=4) by semantically merging related skills.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, List, Set

from dotenv import load_dotenv

from src.aggregator import Aggregator, apply_mapping_to_q_vector
from src.io_utils import ensure_dir, read_json, read_jsonl, write_json
from src.llm_client import LLMClient

JsonDict = Dict[str, Any]


def extract_final_skill_ids(dossier: JsonDict) -> Set[str]:
    """Extract skill IDs from judge's final_skills."""
    judge = dossier.get("judge", {})
    final = judge.get("final_skills", [])
    
    skill_ids = set()
    for item in final:
        if isinstance(item, dict):
            sid = str(item.get("skill_id", "")).strip()
        else:
            sid = str(item).strip()
        if sid:
            skill_ids.add(sid)
    
    return skill_ids


def export_q_matrix(
    dossiers: List[JsonDict],
    skill_ids: List[str],
    output_path: Path,
) -> None:
    """Export Q-matrix CSV."""
    rows = []
    for dossier in dossiers:
        item_id = str(dossier.get("item_id", "")).strip()
        final_ids = extract_final_skill_ids(dossier)
        row = {"item_id": item_id}
        for sid in skill_ids:
            row[sid] = 1 if sid in final_ids else 0
        rows.append(row)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["item_id"] + skill_ids)
        writer.writeheader()
        writer.writerows(rows)


def export_aggregated_q_matrix(
    dossiers: List[JsonDict],
    original_skill_ids: List[str],
    mapping: Dict[str, str],
    merged_skill_ids: List[str],
    output_path: Path,
) -> None:
    """Export Q-matrix with merged skills."""
    rows = []
    for dossier in dossiers:
        item_id = str(dossier.get("item_id", "")).strip()
        final_ids = extract_final_skill_ids(dossier)
        
        # Create original Q-vector
        orig_q = {sid: (1 if sid in final_ids else 0) for sid in original_skill_ids}
        
        # Apply mapping to get merged Q-vector
        merged_q = apply_mapping_to_q_vector(orig_q, mapping)
        
        row = {"item_id": item_id}
        for mid in merged_skill_ids:
            row[mid] = merged_q.get(mid, 0)
        rows.append(row)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["item_id"] + merged_skill_ids)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create multiple K-level codebooks by aggregating skills."
    )
    parser.add_argument(
        "--codebook",
        default="outputs/step3_skill_codebook.json",
        help="Input fine-grained codebook (K_max)",
    )
    parser.add_argument(
        "--dossiers",
        default="outputs/step5_judge_adjudicated_dossiers.jsonl",
        help="Adjudicated dossiers JSONL",
    )
    parser.add_argument(
        "--target_k",
        type=str,
        default="6,5,4",
        help="Comma-separated target K values (e.g., '6,5,4')",
    )
    parser.add_argument(
        "--out_dir",
        default="outputs",
        help="Output directory",
    )
    parser.add_argument(
        "--prompts_dir",
        default="prompts/v2",
        help="Directory containing prompt files",
    )
    args = parser.parse_args()

    load_dotenv(override=False)
    
    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)
    
    # Parse target K values
    target_k_values = [int(k.strip()) for k in args.target_k.split(",")]
    
    # Load inputs
    codebook = read_json(args.codebook)
    dossiers = read_jsonl(args.dossiers)
    
    skills = codebook.get("skills", [])
    source_k = len(skills)
    original_skill_ids = [s.get("skill_id") for s in skills]
    
    print(f"Source codebook: K={source_k}")
    print(f"Target K values: {target_k_values}")
    
    # Filter target_k to only those smaller than source_k
    valid_targets = [k for k in target_k_values if k < source_k]
    if not valid_targets:
        print(f"No valid target K values (all >= source K={source_k})")
        print("Exporting only the original K-matrix...")
        
        # Export original Q-matrix
        export_q_matrix(
            dossiers=dossiers,
            skill_ids=original_skill_ids,
            output_path=out_dir / f"step6_Q_matrix_K{source_k}.csv",
        )
        print(f"  ✓ Exported Q_K{source_k}.csv")
        return
    
    # Run Aggregator
    print(f"\n=== Running Aggregator for K={valid_targets} ===")
    
    llm = LLMClient()
    aggregator = Aggregator(
        llm=llm,
        prompt_path=str(Path(args.prompts_dir) / "aggregator.txt"),
    )
    
    agg_output = aggregator.aggregate(
        codebook=codebook,
        target_k_values=valid_targets,
        dossiers=dossiers,
    )
    
    # Save aggregator output
    write_json(out_dir / "step6_aggregator_output.json", agg_output)
    print(f"Aggregator output saved to: {out_dir}/step6_aggregator_output.json")
    
    # Export original Q-matrix (K_max)
    print(f"\n=== Exporting Q-matrices ===")
    export_q_matrix(
        dossiers=dossiers,
        skill_ids=original_skill_ids,
        output_path=out_dir / f"step6_Q_matrix_K{source_k}.csv",
    )
    print(f"  ✓ Exported Q_K{source_k}.csv (original)")
    
    # Export aggregated Q-matrices
    for agg_codebook in agg_output.get("aggregated_codebooks", []):
        target_k = agg_codebook.get("target_k")
        mapping = agg_codebook.get("mapping", {})
        merged_skills = agg_codebook.get("skills", [])
        merged_ids = [s.get("merged_id") for s in merged_skills]
        
        export_aggregated_q_matrix(
            dossiers=dossiers,
            original_skill_ids=original_skill_ids,
            mapping=mapping,
            merged_skill_ids=merged_ids,
            output_path=out_dir / f"step6_Q_matrix_K{target_k}.csv",
        )
        print(f"  ✓ Exported Q_K{target_k}.csv")
        
        # Save merged codebook
        merged_codebook = {
            "version": "v1",
            "domain": codebook.get("domain", ""),
            "source_k": source_k,
            "target_k": target_k,
            "skills": merged_skills,
            "mapping": mapping,
        }
        write_json(out_dir / f"step6_codebook_K{target_k}.json", merged_codebook)
        print(f"  ✓ Saved codebook_K{target_k}.json")
    
    # Print summary
    print(f"\n=== Aggregation Summary ===")
    print(agg_output.get("aggregation_notes", ""))
    
    print(f"\n=== Generated Files ===")
    print(f"  - Q_K{source_k}.csv (original, K={source_k})")
    for agg_codebook in agg_output.get("aggregated_codebooks", []):
        k = agg_codebook.get("target_k")
        print(f"  - Q_K{k}.csv (merged, K={k})")
        print(f"  - codebook_K{k}.json")


if __name__ == "__main__":
    main()
