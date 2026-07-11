"""Single-LLM baselines B1/B2/B3 (framework section 6), emitting contract run dirs.

B1 naive: items + minimal task statement, JSON only.
B2 strong CoT: same information corpus the pipeline collectively receives
  (items + domain/ontology/solver guides), solve -> codebook -> minimal tagging.
B3 self-consistency: N samples of B2 at temperature 0.7, modal-K filter,
  column alignment, per-cell majority vote; codebook from the medoid sample.
"""
import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_stability import _pick_reference, align_matrices  # noqa: E402
from eval.contract import validate_run  # noqa: E402
from eval.convert_legacy import _write_canonical_q  # noqa: E402
from src.agent_utils import load_guides, try_parse_json  # noqa: E402
from src.llm_client import LLMClient, LLMConfig  # noqa: E402

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GUIDE_FILES = ["domain_core.txt", "skill_ontology_guide.txt", "solver_method_guide.txt"]

OUTPUT_SCHEMA_TEXT = """Return ONE JSON object with exactly this structure:
{
  "skills": [
    {"skill_id": "S01", "name": "Short skill name", "definition": "One-sentence definition"}
  ],
  "q_matrix": [
    {"item_id": "FS01", "skills": ["S01", "S02"]}
  ]
}
Rules:
- skill_id values are sequential: S01, S02, S03...
- Every item MUST appear exactly once in q_matrix and require at least one skill.
- Every skill_id used in q_matrix MUST be defined in skills.
- Tag the MINIMAL set of necessary skills per item (avoid over-tagging)."""


def k_constraint_text(k_condition):
    if k_condition == "auto":
        return "You MUST define between 3 and 8 skills (inclusive)."
    k = int(k_condition.removeprefix("fixed_"))
    return f"You MUST define exactly {k} skills - no more, no fewer."


def load_items(path):
    items = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                obj = json.loads(line)
                items.append({"item_id": obj["item_id"], "stem_text": obj["stem_text"]})
    return items


def build_b1_prompt(items, k_condition):
    items_text = "\n".join(f'- {it["item_id"]}: {it["stem_text"]}' for it in items)
    return (
        "You are constructing a Q-matrix for a Cognitive Diagnostic Model (CDM) "
        "in educational assessment.\n\n"
        f"Below are {len(items)} assessment items. Define the skills (knowledge "
        "components) required to solve them, and specify which skills each item requires.\n"
        f"{k_constraint_text(k_condition)}\n\n"
        f"Items:\n{items_text}\n\n"
        f"{OUTPUT_SCHEMA_TEXT}\n"
        "Output ONLY the JSON object, no other text."
    )


def build_b2_prompt(items, k_condition, guides_dir="guides"):
    guides = load_guides(guides_dir, GUIDE_FILES) or ""
    items_text = "\n".join(f'- {it["item_id"]}: {it["stem_text"]}' for it in items)
    return (
        "You are an experienced educator constructing a Q-matrix for a Cognitive "
        "Diagnostic Model (CDM) in educational assessment.\n\n"
        f"=== DOMAIN AND METHOD GUIDES ===\n{guides}\n\n"
        f"=== ITEMS ({len(items)}) ===\n{items_text}\n\n"
        "=== YOUR TASK (work through these steps carefully) ===\n"
        "Step 1 - SOLVE: Solve every item step-by-step, following the solution "
        "conventions in the guides. Identify the cognitive operations each step requires.\n"
        "Step 2 - CODEBOOK: Group the operations into skills. Each skill must be "
        "observable from solution steps, cognitively distinct from the others, "
        "clearly defined, evidenced by at least one item, and generalizable to new "
        "items in this domain. "
        f"{k_constraint_text(k_condition)}\n"
        "Step 3 - TAG: For each item, select the MINIMAL set of skills strictly "
        "necessary to solve it. Do not tag skills that might apply but are not "
        "evidenced by the solution.\n\n"
        "You may reason step by step first. Then end your response with the final "
        f"answer as JSON.\n\n{OUTPUT_SCHEMA_TEXT}"
    )


def parse_baseline_output(text, item_ids):
    """Parse model output -> (skills, matrix). Raises ValueError with a reason."""
    cleaned = re.sub(r"```[a-zA-Z]*", "", text).replace("```", "")
    obj, _err = try_parse_json(cleaned.strip())
    if obj is None:
        # fall back: largest {...} block in the text (B2 may reason before the JSON)
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            obj, _err = try_parse_json(match.group(0))
    if not isinstance(obj, dict):
        raise ValueError("no JSON object found in response")

    skills = obj.get("skills")
    q_rows = obj.get("q_matrix")
    if not isinstance(skills, list) or not skills:
        raise ValueError("missing or empty 'skills'")
    if not isinstance(q_rows, list) or not q_rows:
        raise ValueError("missing or empty 'q_matrix'")

    skill_ids = [s.get("skill_id") for s in skills]
    if len(skill_ids) != len(set(skill_ids)) or any(not sid for sid in skill_ids):
        raise ValueError("skill_id values must be unique and non-empty")
    for s in skills:
        if not s.get("name") or not s.get("definition"):
            raise ValueError(f"skill {s.get('skill_id')} missing name/definition")

    tag_map = {}
    for row in q_rows:
        iid = row.get("item_id")
        tags = row.get("skills", [])
        unknown = [t for t in tags if t not in skill_ids]
        if unknown:
            raise ValueError(f"item {iid} uses undefined skills {unknown}")
        tag_map[iid] = set(tags)

    missing = [iid for iid in item_ids if iid not in tag_map]
    if missing:
        raise ValueError(f"items missing from q_matrix: {missing}")
    empty = [iid for iid in item_ids if not tag_map[iid]]
    if empty:
        raise ValueError(f"items with no skills: {empty}")

    matrix = [[1 if sid in tag_map[iid] else 0 for sid in skill_ids] for iid in item_ids]
    return skills, matrix


def validate_k(skills, k_condition):
    n = len(skills)
    if k_condition == "auto":
        return 3 <= n <= 8
    return n == int(k_condition.removeprefix("fixed_"))


def call_with_repair(client, prompt, item_ids, k_condition, temperature, seed, max_tries=3):
    """Call the LLM; on parse/K failure, retry with error feedback appended."""
    messages = [{"role": "user", "content": prompt}]
    last_error = None
    for _ in range(max_tries):
        raw = client.chat_completions(messages, temperature=temperature, seed=seed)
        try:
            skills, matrix = parse_baseline_output(raw, item_ids)
            if not validate_k(skills, k_condition):
                raise ValueError(
                    f"defined {len(skills)} skills, but constraint is: "
                    f"{k_constraint_text(k_condition)}")
            return skills, matrix, raw
        except ValueError as e:
            last_error = str(e)
            messages = messages + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content":
                    f"Your response was invalid: {last_error}. "
                    "Return a corrected complete JSON object in the required schema."},
            ]
    raise RuntimeError(f"no valid output after {max_tries} tries: {last_error}")


def aggregate_b3(samples):
    """Aggregate B2 samples -> (skills, matrix, meta).

    samples: list of (skills, matrix). Keeps modal-K samples, aligns columns,
    majority-votes each cell (ties break to 0: minimal-tagging convention),
    takes the codebook from the medoid sample.
    """
    from collections import Counter
    k_counts = Counter(len(s) for s, _m in samples)
    modal_k, _ = k_counts.most_common(1)[0]
    kept = [(s, m) for s, m in samples if len(s) == modal_k]
    if len(kept) < 2:
        raise RuntimeError(f"only {len(kept)} samples at modal K={modal_k}; need >= 2")

    matrices = [m for _s, m in kept]
    aligned, ref_idx, perms = align_matrices(matrices)
    n_votes = len(aligned)
    n_items, n_skills = len(aligned[0]), len(aligned[0][0])
    final = [[1 if sum(mat[i][j] for mat in aligned) * 2 > n_votes else 0
              for j in range(n_skills)] for i in range(n_items)]

    ref_skills_raw = kept[ref_idx][0]
    ref_perm = perms[ref_idx]  # identity for the reference
    skills = [ref_skills_raw[p] for p in ref_perm]

    meta = {
        "n_samples_total": len(samples),
        "k_distribution": {str(k): c for k, c in sorted(k_counts.items())},
        "modal_k": modal_k,
        "n_samples_used": len(kept),
        "medoid_sample_index": ref_idx,
    }
    return skills, final, meta


def make_client(provider, model):
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        base_url = None
    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        base_url = os.getenv("OPENROUTER_BASE_URL", OPENROUTER_BASE_URL)
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY missing from environment/.env")
    else:
        raise ValueError(f"unknown provider {provider}")
    return LLMClient(LLMConfig(api_key=api_key, model=model, base_url=base_url))


def run_baseline(args):
    from dotenv import load_dotenv
    load_dotenv(override=False)

    items = load_items(args.items)
    item_ids = [it["item_id"] for it in items]
    model_slug = args.model.replace("/", "_").replace(".", "-")
    method = {"b1": "b1_naive", "b2": "b2_cot",
              "b3": f"b3_sc{args.n_samples}"}[args.baseline]

    n_ok = 0
    for run_idx in range(1, args.runs + 1):
        out_dir = Path(args.out) / f"{method}_{model_slug}_{args.k_condition}_run{run_idx}"
        if out_dir.exists() and not validate_run(out_dir):
            print(f"SKIP    {out_dir} (already valid)")
            n_ok += 1
            continue
        out_dir.mkdir(parents=True, exist_ok=True)

        client = make_client(args.provider, args.model)
        use_seed = args.provider == "openai"
        run_seed = args.seed_base + run_idx if use_seed else None
        extras = {}

        try:
            if args.baseline == "b1":
                prompt = build_b1_prompt(items, args.k_condition)
                skills, matrix, _ = call_with_repair(
                    client, prompt, item_ids, args.k_condition,
                    args.temperature, run_seed)
            elif args.baseline == "b2":
                prompt = build_b2_prompt(items, args.k_condition, args.guides_dir)
                skills, matrix, _ = call_with_repair(
                    client, prompt, item_ids, args.k_condition,
                    args.temperature, run_seed)
            else:  # b3
                prompt = build_b2_prompt(items, args.k_condition, args.guides_dir)
                samples, sample_records = [], []
                for s_idx in range(args.n_samples):
                    s_seed = (args.seed_base + run_idx * 1000 + s_idx) if use_seed else None
                    try:
                        s_skills, s_matrix, _ = call_with_repair(
                            client, prompt, item_ids, args.k_condition,
                            args.b3_temperature, s_seed, max_tries=2)
                        samples.append((s_skills, s_matrix))
                        sample_records.append({"k": len(s_skills), "seed": s_seed,
                                               "skills": s_skills, "matrix": s_matrix})
                    except RuntimeError as e:
                        sample_records.append({"error": str(e)[:200], "seed": s_seed})
                skills, matrix, b3_meta = aggregate_b3(samples)
                extras["b3"] = b3_meta
                with open(out_dir / "b3_samples.json", "w") as f:
                    json.dump(sample_records, f, indent=2)
        except RuntimeError as e:
            print(f"FAILED  {out_dir}: {e}")
            with open(out_dir / "FAILED.txt", "w") as f:
                f.write(str(e))
            continue

        skill_ids = [s["skill_id"] for s in skills]
        _write_canonical_q(item_ids, skill_ids, matrix, out_dir / "Q.csv")
        with open(out_dir / "codebook.json", "w") as f:
            json.dump({"skills": skills}, f, indent=2)
        config = {
            "method": method,
            "dataset": args.dataset,
            "k_condition": args.k_condition,
            "k_selected": len(skill_ids),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "method_version": "phase2-v1",
            "model": args.model,
            "provider": args.provider,
            "temperature": args.b3_temperature if args.baseline == "b3" else args.temperature,
            "temperature_fallbacks": client.temperature_fallbacks,
            "seed": run_seed if args.baseline != "b3" else None,
            "seed_base": args.seed_base if use_seed else None,
            "token_cost": dict(client.usage),
            **extras,
        }
        with open(out_dir / "config.json", "w") as f:
            json.dump(config, f, indent=2)

        violations = validate_run(out_dir)
        if violations:
            print(f"INVALID {out_dir}: {violations}")
        else:
            n_ok += 1
            print(f"OK      {out_dir} (K={len(skill_ids)}, "
                  f"tokens in/out {client.usage['input']}/{client.usage['output']})")

    print(f"{n_ok}/{args.runs} runs OK for {method} on {args.model} [{args.k_condition}]")
    return n_ok


def main():
    parser = argparse.ArgumentParser(description="Single-LLM baselines B1/B2/B3.")
    parser.add_argument("--baseline", required=True, choices=["b1", "b2", "b3"])
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", default="openai", choices=["openai", "openrouter"])
    parser.add_argument("--k_condition", default="fixed_4")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--out", required=True)
    parser.add_argument("--items", default="data/items.jsonl")
    parser.add_argument("--dataset", default="tatsuoka")
    parser.add_argument("--guides_dir", default="guides")
    parser.add_argument("--n_samples", type=int, default=5, help="B3 sample count")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--b3_temperature", type=float, default=0.7)
    parser.add_argument("--seed_base", type=int, default=1)
    args = parser.parse_args()

    n_ok = run_baseline(args)
    sys.exit(0 if n_ok == args.runs else 1)


if __name__ == "__main__":
    main()
