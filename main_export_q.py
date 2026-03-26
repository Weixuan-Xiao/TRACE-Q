"""
Export reliability reports for Q-matrix.

Works with flat codebooks (K=3-8).
Q-matrices are exported by the Aggregator stage.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Set

from src.io_utils import ensure_dir, read_json, read_jsonl

JsonDict = Dict[str, Any]


def jaccard(a: Set[str], b: Set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def vote_skill_set(vote: JsonDict) -> Set[str]:
    """Extract skill IDs from a tagger vote."""
    skills = vote.get("skills", [])
    result = set()
    for s in skills:
        if isinstance(s, dict):
            sid = str(s.get("skill_id", "")).strip()
        else:
            sid = str(s).strip()
        if sid:
            result.add(sid)
    return result


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


def compute_reliability_stats(dossiers: List[JsonDict]) -> Dict[str, Any]:
    """Compute inter-rater reliability statistics."""
    n_items = len(dossiers)
    full_agree = 0
    supermajority = 0
    adjudicated_needed = 0
    jaccard_sum = 0.0
    jaccard_count = 0
    
    for d in dossiers:
        votes = d.get("tagger_votes", {})
        tagger_ids = [f"T{i}" for i in range(1, 6)]
        skill_sets = {tid: vote_skill_set(votes.get(tid, {})) for tid in tagger_ids}
        sets_list = list(skill_sets.values())
        
        # Full agreement (all 5 equal)
        if all(s == sets_list[0] for s in sets_list[1:]):
            full_agree += 1
            supermajority += 1
        else:
            # Supermajority: >= 4/5 share same set
            counts = Counter([frozenset(s) for s in sets_list])
            if counts and counts.most_common(1)[0][1] >= 4:
                supermajority += 1
            else:
                adjudicated_needed += 1
        
        # Average pairwise Jaccard
        for i in range(len(sets_list)):
            for j in range(i + 1, len(sets_list)):
                jaccard_sum += jaccard(sets_list[i], sets_list[j])
                jaccard_count += 1
    
    return {
        "n_items": n_items,
        "full_agree": full_agree,
        "supermajority": supermajority,
        "adjudicated_needed": adjudicated_needed,
        "avg_jaccard": jaccard_sum / jaccard_count if jaccard_count else 0.0,
    }


def generate_reliability_report(
    dossiers: List[JsonDict],
    codebook: JsonDict,
    stats: Dict[str, Any],
) -> str:
    """Generate markdown reliability report."""
    lines = []
    n = stats["n_items"]
    skills = codebook.get("skills", [])
    skill_ids = [s.get("skill_id") for s in skills]
    
    lines.append("# Q-Matrix Reliability Report")
    lines.append("")
    lines.append(f"## Codebook Summary")
    lines.append(f"- Domain: {codebook.get('domain', 'N/A')}")
    lines.append(f"- Number of skills (K): {len(skills)}")
    lines.append("")
    
    lines.append("## Inter-Rater Reliability")
    lines.append("")
    lines.append(f"- N items: {n}")
    lines.append(f"- Full agreement rate (5/5): {stats['full_agree'] / n:.3f}")
    lines.append(f"- Supermajority rate (>=4/5): {stats['supermajority'] / n:.3f}")
    lines.append(f"- Adjudication rate: {stats['adjudicated_needed'] / n:.3f}")
    lines.append(f"- Average pairwise Jaccard: {stats['avg_jaccard']:.3f}")
    lines.append("")
    
    # Skill reference
    lines.append("## Skill Codebook")
    lines.append("")
    lines.append("| skill_id | name | definition |")
    lines.append("|----------|------|------------|")
    for skill in skills:
        sid = skill.get("skill_id", "")
        name = skill.get("name", "")
        defn = skill.get("definition", "").replace("|", "\\|")
        lines.append(f"| {sid} | {name} | {defn} |")
    lines.append("")
    
    # Per-skill frequency
    final_freq = Counter()
    for d in dossiers:
        for sid in extract_final_skill_ids(d):
            final_freq[sid] += 1
    
    lines.append("## Per-Skill Frequency in Final Q")
    lines.append("")
    lines.append("| skill_id | name | count | rate |")
    lines.append("|----------|------|------:|-----:|")
    for skill in skills:
        sid = skill.get("skill_id", "")
        name = skill.get("name", "")
        c = final_freq.get(sid, 0)
        lines.append(f"| {sid} | {name} | {c} | {c / n:.3f} |")
    lines.append("")
    
    # Items needing adjudication
    lines.append("## Items Requiring Adjudication")
    lines.append("")
    for d in dossiers:
        votes = d.get("tagger_votes", {})
        sets_list = [vote_skill_set(votes.get(f"T{i}", {})) for i in range(1, 6)]
        counts = Counter([frozenset(s) for s in sets_list])
        if counts and counts.most_common(1)[0][1] >= 4:
            continue
        item_id = d.get("item_id", "")
        tagger_summary = "; ".join([
            f"T{i}={sorted(vote_skill_set(votes.get(f'T{i}', {})))}"
            for i in range(1, 6)
        ])
        lines.append(f"- {item_id}: {tagger_summary}")
    lines.append("")
    
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export reliability report.")
    parser.add_argument(
        "--dossiers",
        default="outputs/step5_judge_adjudicated_dossiers.jsonl",
        help="Adjudicated dossiers JSONL",
    )
    parser.add_argument(
        "--codebook",
        default="outputs/step3_skill_codebook.json",
        help="Codebook JSON",
    )
    parser.add_argument(
        "--out_dir",
        default="outputs",
        help="Output directory",
    )
    parser.add_argument(
        "--prefix",
        default="step7_export",
        help="Output filename prefix",
    )
    args = parser.parse_args()
    
    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)
    
    codebook = read_json(args.codebook)
    dossiers = read_jsonl(args.dossiers)
    
    if not dossiers:
        raise RuntimeError("No adjudicated dossiers found.")
    
    skills = codebook.get("skills", [])
    skill_ids = [s.get("skill_id") for s in skills]
    
    print(f"Generating reliability report for K={len(skills)} codebook...")
    
    # Compute reliability stats
    stats = compute_reliability_stats(dossiers)
    
    # Generate and save reliability report
    report = generate_reliability_report(dossiers, codebook, stats)
    report_path = out_dir / f"{args.prefix}_reliability_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  - {report_path}")
    
    # Export per-item reliability CSV
    items_csv_path = out_dir / f"{args.prefix}_reliability_per_item.csv"
    with open(items_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "item_id", "T1_skills", "T2_skills", "T3_skills", "T4_skills", "T5_skills",
            "full_agree", "supermajority", "avg_jaccard", "final_skills",
        ])
        
        for d in dossiers:
            item_id = d.get("item_id", "")
            votes = d.get("tagger_votes", {})
            sets_list = [vote_skill_set(votes.get(f"T{i}", {})) for i in range(1, 6)]
            
            full5 = 1 if all(s == sets_list[0] for s in sets_list[1:]) else 0
            counts = Counter([frozenset(s) for s in sets_list])
            supermaj = 1 if (counts and counts.most_common(1)[0][1] >= 4) else 0
            
            jac_sum = sum(
                jaccard(sets_list[i], sets_list[j])
                for i in range(5) for j in range(i + 1, 5)
            )
            avg_jac = jac_sum / 10
            
            final_ids = sorted(extract_final_skill_ids(d))
            
            writer.writerow([
                item_id,
                " ".join(sorted(sets_list[0])),
                " ".join(sorted(sets_list[1])),
                " ".join(sorted(sets_list[2])),
                " ".join(sorted(sets_list[3])),
                " ".join(sorted(sets_list[4])),
                full5,
                supermaj,
                f"{avg_jac:.3f}",
                " ".join(final_ids),
            ])
    
    print(f"  - {items_csv_path}")
    print("Export complete.")


if __name__ == "__main__":
    main()
