from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from tqdm import tqdm

from src.io_utils import append_jsonl, ensure_dir, read_jsonl
from src.llm_client import LLMClient
from src.verifier import Verifier

JsonDict = Dict[str, Any]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Verifier over solver dossiers.")
    parser.add_argument("--input", default="outputs/step1_solver_item_dossiers.jsonl", help="Input solver dossiers JSONL")
    parser.add_argument("--out", default="outputs/step2_verifier_verified_item_dossiers.jsonl", help="Output verified dossiers JSONL")
    parser.add_argument("--prompts_dir", default="prompts/v1", help="Directory containing prompt files (verifier.txt, etc.)")
    args = parser.parse_args()

    load_dotenv(override=False)
    ensure_dir(str(Path(args.out).parent))
    # Always from scratch: overwrite output file.
    Path(args.out).unlink(missing_ok=True)
    seen_item_ids: set[str] = set()

    rows = read_jsonl(args.input)
    llm = LLMClient()
    verifier = Verifier(llm=llm, prompt_path=str(Path(args.prompts_dir) / "verifier.txt"))

    for row in tqdm(rows, desc="Verifying", unit="item"):
        item = row.get("item", {})
        solver = row.get("solver", {})
        item_id = str(row.get("item_id", item.get("item_id", ""))).strip()
        if not item_id:
            raise ValueError(f"Missing item_id in row: {row}")
        if item_id in seen_item_ids:
            continue

        ver_out = verifier.verify(item=item, solver=solver)

        ok = bool(ver_out.get("ok"))
        corrected_solver = ver_out.get("corrected_solver")
        solver_final = solver if ok or corrected_solver is None else corrected_solver
        corrected_flag = (not ok) and (corrected_solver is not None)

        verified = {
            "item_id": item_id,
            "item": item,
            "solver": solver_final,
            "verifier": {
                "ok": ok,
                "issues": ver_out.get("issues", []),
                "corrected": corrected_flag,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "stage": "verified",
        }

        append_jsonl(args.out, [verified])
        seen_item_ids.add(item_id)


if __name__ == "__main__":
    main()
