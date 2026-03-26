"""
generate_run_summary.py
========================
Generates a human-readable run_summary.md from a single pipeline run's outputs.

Usage:
    python generate_run_summary.py <run_dir>
    python generate_run_summary.py outputs_exp/v1/run1

The summary traces each item's full journey:
  Item → Solution → Verification → Codebook → Tagger Votes → Judge → Audit
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


# ── I/O helpers ──────────────────────────────────────────────────────────────

def read_jsonl(path):
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_csv_rows(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def safe_read_jsonl(path):
    return read_jsonl(path) if os.path.exists(path) else []


def safe_read_json(path):
    return read_json(path) if os.path.exists(path) else {}


def safe_read_csv(path):
    return read_csv_rows(path) if os.path.exists(path) else []


# ── Data loaders ─────────────────────────────────────────────────────────────

def find_first(rd, *candidates):
    """Return the first existing file path from candidates, or None."""
    for c in candidates:
        matches = list(rd.glob(c)) if "*" in c else ([rd / c] if (rd / c).exists() else [])
        if matches:
            return matches[0]
    return None


def load_run(run_dir):
    """Load all outputs from a single run directory into a unified dict."""
    rd = Path(run_dir)

    data = {}

    # Meta
    data["meta"] = safe_read_json(rd / "run_meta.json")

    # Step 1: Solver dossiers
    data["solver_dossiers"] = {
        d["item_id"]: d
        for d in safe_read_jsonl(rd / "step1_solver_item_dossiers.jsonl")
    }

    # Step 2: Verified dossiers
    data["verified_dossiers"] = {
        d["item_id"]: d
        for d in safe_read_jsonl(rd / "step2_verifier_verified_item_dossiers.jsonl")
    }

    # Step 3: Expert codebooks + supervisor + final codebook
    data["expert_codebooks"] = safe_read_json(rd / "step3_expert_codebooks.json")
    data["supervisor_output"] = safe_read_json(rd / "step3_supervisor_output.json")
    # Codebook: try multiple naming conventions
    codebook_path = find_first(rd,
        "step3_skill_codebook.json",
        "step3_taxonomist_skill_codebook_v1.json",
        "step3_taxonomist_skill_codebook*.json",
    )
    data["codebook"] = read_json(codebook_path) if codebook_path else {}

    # Step 4: Tagger votes
    tagger_dir = rd / "step4_tagger_votes"
    data["tagger_votes"] = {}
    if tagger_dir.exists():
        for tf in sorted(tagger_dir.glob("T*.jsonl")):
            tid = tf.stem  # T1, T2, ...
            votes_by_item = {}
            for v in read_jsonl(tf):
                votes_by_item[v["item_id"]] = v
            data["tagger_votes"][tid] = votes_by_item

    # Step 5: Judge adjudicated dossiers
    data["judge_dossiers"] = {
        d["item_id"]: d
        for d in safe_read_jsonl(rd / "step5_judge_adjudicated_dossiers.jsonl")
    }

    # Step 6: Q-matrix (try multiple naming patterns)
    q_path = find_first(rd,
        "step6_Q_matrix_K*.csv",
        "step6_export_Q_matrix*.csv",
    )
    data["q_matrix"] = {}
    if q_path:
        for row in read_csv_rows(q_path):
            item_id = row.pop("item_id")
            data["q_matrix"][item_id] = row

    # Reliability (step6 or step7 prefix)
    rel_path = find_first(rd,
        "step6_export_reliability_per_item.csv",
        "step7_export_reliability_per_item.csv",
    )
    data["reliability"] = {}
    if rel_path:
        for row in read_csv_rows(rel_path):
            data["reliability"][row["item_id"]] = row

    # Auditor review (step7 or step8 prefix)
    auditor_review_files = list(rd.glob("step7_auditor_review*.jsonl")) + \
                           list(rd.glob("step8_auditor_review*.jsonl"))
    data["auditor_reviews"] = {}
    for af in auditor_review_files:
        for d in read_jsonl(af):
            data["auditor_reviews"][d["item_id"]] = d

    # Auditor Q-matrix (step7 or step8 prefix)
    auditor_q_files = list(rd.glob("step7_auditor_Q_matrix*.csv")) + \
                      list(rd.glob("step8_auditor_Q_matrix*.csv"))
    data["auditor_q"] = {}
    if auditor_q_files:
        for row in read_csv_rows(auditor_q_files[0]):
            item_id = row.pop("item_id")
            data["auditor_q"][item_id] = row

    # Collect item_ids in order
    data["item_ids"] = sorted(data["judge_dossiers"].keys(),
                              key=lambda x: (len(x), x))
    if not data["item_ids"]:
        data["item_ids"] = sorted(data["verified_dossiers"].keys(),
                                  key=lambda x: (len(x), x))

    return data


# ── Formatting helpers ───────────────────────────────────────────────────────

def fmt_steps(steps):
    """Format solution steps as compact lines."""
    lines = []
    for s in steps:
        lines.append(f"  {s['step_id']}: {s['text']}")
    return "\n".join(lines)


def fmt_skill_list(skill_ids, codebook_skills):
    """Format skill IDs with names: S01 (Convert mixed numbers...)"""
    skill_map = {s["skill_id"]: s["name"] for s in codebook_skills}
    parts = []
    for sid in skill_ids:
        name = skill_map.get(sid, "?")
        parts.append(f"{sid} ({name})")
    return ", ".join(parts) if parts else "(none)"


def fmt_tagger_row(tagger_id, vote, codebook_skills):
    """Format one tagger's vote as a compact line."""
    skill_map = {s["skill_id"]: s["name"] for s in codebook_skills}
    skills = vote.get("vote", vote).get("skills", []) if isinstance(vote.get("vote"), dict) else vote.get("skills", [])
    parts = []
    for s in skills:
        sid = s["skill_id"]
        step_ids = ", ".join(s.get("evidence_step_ids", []))
        parts.append(f"{sid}[{step_ids}]")
    skill_str = ", ".join(parts) if parts else "(none)"

    # Optional skills
    opt = vote.get("vote", vote).get("optional_skills", []) if isinstance(vote.get("vote"), dict) else vote.get("optional_skills", [])
    opt_ids = [o.get("skill_id", o) if isinstance(o, dict) else o for o in opt]
    opt_str = f"  optional: {', '.join(opt_ids)}" if opt_ids else ""

    return f"  {tagger_id}: {skill_str}{opt_str}"


def build_vote_summary(item_id, tagger_votes, codebook_skills):
    """Build a skill-level vote count summary across taggers."""
    skill_counts = defaultdict(list)
    tagger_ids = sorted(tagger_votes.keys())

    for tid in tagger_ids:
        vote_data = tagger_votes[tid].get(item_id)
        if not vote_data:
            continue
        # Handle nested vote structure
        vote = vote_data.get("vote", vote_data)
        skills = vote.get("skills", [])
        for s in skills:
            skill_counts[s["skill_id"]].append(tid)

    lines = []
    skill_map = {s["skill_id"]: s["name"] for s in codebook_skills}
    all_sids = sorted(skill_map.keys())
    for sid in all_sids:
        taggers = skill_counts.get(sid, [])
        count = len(taggers)
        if count == 0:
            continue
        tag = ""
        if count >= 4:
            tag = " → auto-include"
        elif count <= 1:
            tag = " → auto-exclude"
        else:
            tag = " → DISPUTED"
        lines.append(f"  {sid} ({skill_map[sid]}): {count}/5 [{', '.join(taggers)}]{tag}")

    return "\n".join(lines)


# ── Main summary generator ──────────────────────────────────────────────────

def generate_summary(data):
    lines = []
    w = lines.append  # shorthand

    meta = data["meta"]
    codebook = data["codebook"]
    codebook_skills = codebook.get("skills", [])
    skill_map = {s["skill_id"]: s["name"] for s in codebook_skills}

    # ── Header ───────────────────────────────────────────────────────────
    w("# Run Summary")
    w("")
    if meta:
        w(f"- **Prompt version**: {meta.get('prompt_version', '?')}")
        w(f"- **Run index**: {meta.get('run_index', '?')}")
        w(f"- **Created**: {meta.get('created_at', '?')}")
        w(f"- **Command**: `{meta.get('cmd', '?')}`")
        w("")

    # ── Codebook overview ────────────────────────────────────────────────
    w("## Skill Codebook (K=%d)" % len(codebook_skills))
    w("")
    w("| ID | Skill Name | Definition |")
    w("|----|-----------|------------|")
    for s in codebook_skills:
        defn = s.get("definition", "")
        # Truncate long definitions for table readability
        if len(defn) > 120:
            defn = defn[:117] + "..."
        w(f"| {s['skill_id']} | {s['name']} | {defn} |")
    w("")

    # ── Q-Matrix overview ────────────────────────────────────────────────
    w("## Q-Matrix Overview")
    w("")
    skill_ids = [s["skill_id"] for s in codebook_skills]
    header = "| Item | " + " | ".join(skill_ids) + " | Audit |"
    sep = "|------|" + "|".join(["---"] * len(skill_ids)) + "|-------|"
    w(header)
    w(sep)

    for item_id in data["item_ids"]:
        q_row = data["q_matrix"].get(item_id, {})
        aq_row = data["auditor_q"].get(item_id, {})
        audit_verdict = aq_row.get("audit_verdict", "—")

        cells = []
        for sid in skill_ids:
            pre = q_row.get(sid, "—")
            post = aq_row.get(sid, pre)
            # Mark cells that changed after audit
            if str(post).replace("*", "") != str(pre) and post != pre:
                cells.append(f"**{post}**")
            elif "*" in str(post):
                cells.append(f"{post}")
            else:
                cells.append(str(pre))

        verdict_marker = ""
        if audit_verdict == "error":
            verdict_marker = "ERROR"
        elif audit_verdict == "controversial":
            verdict_marker = "CONTROV"
        elif audit_verdict == "correct":
            verdict_marker = "ok"
        else:
            verdict_marker = audit_verdict

        w(f"| {item_id} | " + " | ".join(cells) + f" | {verdict_marker} |")
    w("")

    # ── Pipeline statistics ──────────────────────────────────────────────
    w("## Pipeline Statistics")
    w("")

    # Verifier stats
    n_corrected = sum(
        1 for d in data["verified_dossiers"].values()
        if d.get("verifier", {}).get("ok") is False
    )
    w(f"- **Verifier corrections**: {n_corrected}/{len(data['verified_dossiers'])} items")

    # Tagger agreement stats
    rel = data["reliability"]
    if rel:
        n_full = sum(1 for r in rel.values() if str(r.get("full_agree_5", "0")) == "1")
        n_super = sum(1 for r in rel.values() if str(r.get("supermajority_4of5", "0")) == "1")
        w(f"- **Full tagger agreement (5/5)**: {n_full}/{len(rel)} items")
        w(f"- **Supermajority (≥4/5)**: {n_super}/{len(rel)} items")

    # Audit stats
    audits = data["auditor_reviews"]
    if audits:
        verdicts = defaultdict(int)
        for a in audits.values():
            verdicts[a.get("verdict", "?")] += 1
        parts = [f"{v}: {c}" for v, c in sorted(verdicts.items())]
        w(f"- **Auditor verdicts**: {', '.join(parts)}")
    w("")

    # ── Per-item trace ───────────────────────────────────────────────────
    w("---")
    w("")
    w("## Per-Item Trace")
    w("")

    for item_id in data["item_ids"]:
        w(f"### {item_id}")
        w("")

        # ── Item stem
        dossier = data["verified_dossiers"].get(item_id,
                  data["solver_dossiers"].get(item_id, {}))
        item = dossier.get("item", {})
        w(f"**Problem**: `{item.get('stem_text', '?')}`")
        w("")

        # ── Solution
        solver = dossier.get("solver", {})
        w(f"**Answer**: `{', '.join(solver.get('answer_canonical', ['?']))}`")
        w("")
        w("**Solution steps**:")
        w("```")
        for s in solver.get("solution_steps", []):
            w(f"{s['step_id']}: {s['text']}")
        w("```")
        w("")

        # ── Verification
        ver = dossier.get("verifier", {})
        if ver.get("ok") is False:
            w("**Verifier**: CORRECTED")
            issues = ver.get("issues", [])
            for iss in issues:
                w(f"  - [{iss.get('type', '?')}] {iss.get('detail', '')}")
            w("")
        else:
            w("**Verifier**: ok")
            w("")

        # ── Tagger votes (compact)
        w("**Tagger votes**:")
        w("")
        tagger_ids = sorted(data["tagger_votes"].keys())
        for tid in tagger_ids:
            vote_data = data["tagger_votes"][tid].get(item_id)
            if vote_data:
                w(fmt_tagger_row(tid, vote_data, codebook_skills))
        w("")

        # ── Vote summary
        w("**Vote tally**:")
        w("")
        w(build_vote_summary(item_id, data["tagger_votes"], codebook_skills))
        w("")

        # ── Judge
        judge_data = data["judge_dossiers"].get(item_id, {}).get("judge", {})
        if judge_data:
            final_skills = judge_data.get("final_skills", [])
            skill_strs = []
            for fs in final_skills:
                sid = fs["skill_id"]
                conf = fs.get("confidence", "?")
                name = skill_map.get(sid, "?")
                skill_strs.append(f"{sid} ({name}) conf={conf}")
            w(f"**Judge decision**: {', '.join(skill_strs)}")
            notes = judge_data.get("judge_notes", "")
            if notes:
                w(f"  _{notes}_")
            w("")

        # ── Audit
        audit = data["auditor_reviews"].get(item_id)
        if audit:
            verdict = audit.get("verdict", "?")
            marker = {"correct": "CORRECT", "error": "ERROR",
                      "controversial": "CONTROVERSIAL"}.get(verdict, verdict)
            w(f"**Audit verdict**: **{marker}**")

            corrections = audit.get("corrections", {})
            add = corrections.get("add_skills", [])
            remove = corrections.get("remove_skills", [])
            if add:
                w(f"  - Add: {fmt_skill_list(add, codebook_skills)}")
            if remove:
                w(f"  - Remove: {fmt_skill_list(remove, codebook_skills)}")
            reasoning = corrections.get("reasoning", "")
            if reasoning and verdict != "correct":
                w(f"  - Reason: {reasoning}")
            w("")

        # ── Final Q-vector
        q_row = data["q_matrix"].get(item_id, {})
        aq_row = data["auditor_q"].get(item_id, {})
        if q_row:
            pre_vec = [f"{sid}={q_row.get(sid, '?')}" for sid in skill_ids]
            w(f"**Q-vector (pre-audit)**: {', '.join(pre_vec)}")
        if aq_row:
            post_vec = []
            for sid in skill_ids:
                val = aq_row.get(sid, "?")
                pre_val = q_row.get(sid, "?")
                if str(val).replace("*", "") != str(pre_val):
                    post_vec.append(f"**{sid}={val}**")
                else:
                    post_vec.append(f"{sid}={val}")
            w(f"**Q-vector (post-audit)**: {', '.join(post_vec)}")
        w("")
        w("---")
        w("")

    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate a human-readable run summary from pipeline outputs."
    )
    parser.add_argument("run_dir", help="Path to a run directory (e.g. outputs_exp/v1/run1)")
    parser.add_argument("-o", "--output", default=None,
                        help="Output file path (default: <run_dir>/run_summary.md)")
    args = parser.parse_args()

    run_dir = args.run_dir
    if not os.path.isdir(run_dir):
        print(f"Error: {run_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    data = load_run(run_dir)
    summary = generate_summary(data)

    output_path = args.output or os.path.join(run_dir, "run_summary.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"Summary written to {output_path}")
    print(f"  Items: {len(data['item_ids'])}")
    print(f"  Skills: {len(data['codebook'].get('skills', []))}")


if __name__ == "__main__":
    main()
