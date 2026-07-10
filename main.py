from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from tqdm import tqdm

from src.agent_utils import load_guides
from src.io_utils import append_jsonl, ensure_dir, read_jsonl
from src.llm_client import LLMClient
from src.solver import Solver

JsonDict = Dict[str, Any]


def build_dossier(item: JsonDict, solver_out: JsonDict) -> JsonDict:
    return {
        "item_id": item.get("item_id"),
        "item": item,
        "solver": solver_out,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "stage": "solver",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Solver over items.jsonl (no caching; always from scratch).")
    parser.add_argument("--input", default="data/items.jsonl", help="Input JSONL path")
    parser.add_argument("--out", default="outputs/step1_solver_item_dossiers.jsonl", help="Output JSONL path")
    parser.add_argument("--prompts_dir", default="prompts/v5_guided", help="Directory containing prompt files (solver.txt, etc.)")
    parser.add_argument("--guides_dir", default=None, help="Directory containing guide txt files (optional)")
    args = parser.parse_args()

    load_dotenv(override=False)

    items = read_jsonl(args.input)
    ensure_dir(str(Path(args.out).parent))

    solver_guide = None
    if args.guides_dir:
        solver_guide = load_guides(args.guides_dir, ["domain_core.txt", "solver_method_guide.txt"])

    llm = LLMClient()
    solver = Solver(
        llm=llm,
        prompt_path=str(Path(args.prompts_dir) / "solver.txt"),
        domain_guide=solver_guide,
    )

    # Always from scratch: delete output file if present.
    Path(args.out).unlink(missing_ok=True)

    for item in tqdm(items, desc="Solving", unit="item"):
        item_id = str(item.get("item_id", "")).strip()
        if not item_id:
            raise ValueError(f"Missing item_id in item: {item}")

        solver_out = solver.solve_item(item)

        dossier = build_dossier(item, solver_out)
        append_jsonl(args.out, [dossier])


if __name__ == "__main__":
    main()


