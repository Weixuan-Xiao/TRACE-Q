"""V2: contamination probe (framework section 5).

Asks an LLM to reproduce the published expert Q-matrix for a dataset from
memory. High aligned agreement means the dataset's expert Q is in the model's
training data; interpretation is left to humans.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_stability import load_qmatrix  # noqa: E402
from eval.baselines import make_client  # noqa: E402
from eval.expert_agreement import aligned_agreement  # noqa: E402
from src.llm_client import LLMClient  # noqa: E402

PROMPTS = {
    "tatsuoka": (
        "In cognitive diagnostic modeling research, the Tatsuoka (1990) fraction "
        "subtraction dataset (20 items, 536 examinees) has a well-known published "
        "expert Q-matrix with 8 attributes, as distributed with the GDINA R package "
        "(realdata_Tatsuoka1990). Reproduce that expert Q-matrix exactly, from your "
        "knowledge of the literature.\n\n"
        "Output ONLY raw CSV: a header row 'item,A1,A2,A3,A4,A5,A6,A7,A8' followed by "
        "20 rows (items in the published order), cells strictly 0 or 1. "
        "No explanations, no markdown fences."
    ),
}


def parse_q_csv(text, n_items, n_skills):
    """Tolerant parser: strips code fences, header row, item-id column.

    Returns matrix (list of lists of int) or None if unparseable.
    """
    text = re.sub(r"```[a-zA-Z]*", "", text).replace("```", "")
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        cells = [c.strip() for c in re.split(r"[,\t]", line)]
        binary = [c for c in cells if c in ("0", "1")]
        if len(binary) >= n_skills:
            # A numeric item id (0/1) would sit first; skill cells are the last n_skills.
            rows.append([int(c) for c in binary[-n_skills:]])
    if len(rows) == n_items + 1 and all(v in (0, 1) for v in rows[0]):
        # header row happened to parse as binary — unlikely; drop first row
        rows = rows[1:]
    if len(rows) != n_items:
        return None
    return rows


def probe_model(client, model, dataset, expert_matrix, expert_skills):
    prompt = PROMPTS[dataset]
    raw = client.chat_completions(
        [{"role": "user", "content": prompt}], model=model, temperature=0.0)

    n_items, n_skills = len(expert_matrix), len(expert_matrix[0])
    parsed = parse_q_csv(raw, n_items, n_skills)

    result = {
        "model": model,
        "dataset": dataset,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "prompt": prompt,
        "raw_response": raw,
        "parsed_ok": parsed is not None,
        "exact_cell_agreement": None,
        "aligned_cell_agreement": None,
    }
    if parsed is not None:
        n_cells = n_items * n_skills
        exact = sum(
            parsed[i][j] == expert_matrix[i][j]
            for i in range(n_items) for j in range(n_skills)
        ) / n_cells
        result["exact_cell_agreement"] = round(exact, 4)
        agreement = aligned_agreement(parsed, expert_matrix, None, expert_skills)
        result["aligned_cell_agreement"] = agreement["cell_agreement"]
        result["aligned_detail"] = agreement
    return result


def main():
    parser = argparse.ArgumentParser(description="V2 contamination probe.")
    parser.add_argument("--dataset", default="tatsuoka", choices=sorted(PROMPTS))
    parser.add_argument("--expert_q", default="data/expert_q_tatsuoka.csv")
    parser.add_argument("--models", default=None,
                        help="Comma-separated model list (default: OPENAI_MODEL from .env)")
    parser.add_argument("--provider", default="openai", choices=["openai", "openrouter"])
    parser.add_argument("--out", default="eval_out/v2")
    args = parser.parse_args()

    _items, expert_skills, expert_matrix = load_qmatrix(args.expert_q)
    if args.models:
        models = [m.strip() for m in args.models.split(",")]
    else:
        models = [LLMClient().config.model]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for model in models:
        client = make_client(args.provider, model)
        print(f"Probing {model} on {args.dataset} ...")
        result = probe_model(client, model, args.dataset, expert_matrix, expert_skills)
        ts = result["timestamp"].replace(":", "").split(".")[0]
        out_path = out_dir / f"{model.replace('/', '_')}_{ts}.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"  parsed_ok={result['parsed_ok']} "
              f"exact={result['exact_cell_agreement']} "
              f"aligned={result['aligned_cell_agreement']}")
        print(f"  archived: {out_path}")


if __name__ == "__main__":
    main()
