from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from tqdm import tqdm

from src.io_utils import append_jsonl, ensure_dir, read_json, read_jsonl
from src.llm_client import LLMClient
from src.tagger import Tagger

JsonDict = Dict[str, Any]


def run_one_tagger(
    *,
    tagger_id: str,
    codebook: JsonDict,
    dossiers: List[JsonDict],
    out_path: str,
    prompts_dir: str,
) -> str:
    """
    Run a single tagger over all dossiers.
    Returns the tagger_id when complete.
    
    Each tagger creates its own LLMClient to avoid thread-safety issues.
    """
    # Each thread gets its own LLM client
    llm = LLMClient()
    
    ensure_dir(Path(out_path).parent)
    Path(out_path).unlink(missing_ok=True)
    seen: set[str] = set()

    tagger = Tagger(llm=llm, tagger_id=tagger_id, prompt_path=str(Path(prompts_dir) / "tagger.txt"))

    for d in dossiers:
        item_id = str(d.get("item_id", "")).strip()
        if not item_id:
            raise ValueError(f"Missing item_id in dossier: {d}")
        if item_id in seen:
            continue

        vote = tagger.tag(codebook=codebook, dossier=d)

        row = {
            "item_id": item_id,
            "tagger_id": tagger_id,
            "vote": vote,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "stage": "tagger_vote",
        }
        append_jsonl(out_path, [row])
        seen.add(item_id)
    
    return tagger_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 5 taggers (T1..T5) to produce votes.")
    parser.add_argument("--dossiers", default="outputs/step2_verifier_verified_item_dossiers.jsonl", help="Verified dossiers JSONL")
    parser.add_argument("--codebook", default="outputs/step3_taxonomist_skill_codebook_v1.json", help="Codebook JSON")
    parser.add_argument("--out_dir", default="outputs/step4_tagger_votes", help="Output directory for tagger votes")
    parser.add_argument("--parallel", action="store_true", help="Run taggers in parallel (faster but uses more API calls concurrently)")
    parser.add_argument("--prompts_dir", default="prompts/v1", help="Directory containing prompt files (tagger.txt, etc.)")
    parser.add_argument("--n_taggers", type=int, default=5, help="Number of taggers to run (default: 5)")
    args = parser.parse_args()

    load_dotenv(override=False)
    ensure_dir("outputs")
    ensure_dir(args.out_dir)

    dossiers = read_jsonl(args.dossiers)
    codebook = read_json(args.codebook)

    tagger_ids = [f"T{i+1}" for i in range(args.n_taggers)]

    if args.parallel:
        # Parallel execution: 5 taggers run concurrently
        print(f"Running {len(tagger_ids)} taggers in parallel...")
        with ThreadPoolExecutor(max_workers=args.n_taggers) as executor:
            futures = {}
            for tid in tagger_ids:
                out_path = str(Path(args.out_dir) / f"{tid}.jsonl")
                future = executor.submit(
                    run_one_tagger,
                    tagger_id=tid,
                    codebook=codebook,
                    dossiers=dossiers,
                    out_path=out_path,
                    prompts_dir=args.prompts_dir,
                )
                futures[future] = tid

            # Wait for all taggers to complete with progress
            for future in tqdm(as_completed(futures), total=len(futures), desc="Taggers", unit="tagger"):
                tid = futures[future]
                try:
                    future.result()
                    print(f"  ✓ {tid} completed")
                except Exception as e:
                    print(f"  ✗ {tid} failed: {e}")
                    raise
    else:
        # Sequential execution: one tagger at a time (original behavior)
        llm = LLMClient()
        for tid in tagger_ids:
            out_path = str(Path(args.out_dir) / f"{tid}.jsonl")
            print(f"Running {tid}...")
            
            ensure_dir(Path(out_path).parent)
            Path(out_path).unlink(missing_ok=True)
            seen: set[str] = set()
            tagger = Tagger(llm=llm, tagger_id=tid, prompt_path=str(Path(args.prompts_dir) / "tagger.txt"))

            for d in tqdm(dossiers, desc=f"Tagging {tid}", unit="item"):
                item_id = str(d.get("item_id", "")).strip()
                if not item_id:
                    raise ValueError(f"Missing item_id in dossier: {d}")
                if item_id in seen:
                    continue

                vote = tagger.tag(codebook=codebook, dossier=d)
                row = {
                    "item_id": item_id,
                    "tagger_id": tid,
                    "vote": vote,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "stage": "tagger_vote",
                }
                append_jsonl(out_path, [row])
                seen.add(item_id)


if __name__ == "__main__":
    main()
