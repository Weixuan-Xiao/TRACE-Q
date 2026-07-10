"""Four-layer stability over contract run directories (framework section 4).

Layers: K distribution -> codebook semantic matching -> matrix (aligned kappa
etc.) -> classification (pairwise ARI). Every exclusion is recorded, never silent.
"""
import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_stability import compute_stability_from_matrices  # noqa: E402
from eval.contract import discover_runs, load_run  # noqa: E402
from eval.codebook_match import codebook_stability  # noqa: E402
from eval import ari as ari_mod  # noqa: E402


def compute_stability(run_dirs, out_dir, dataset="tatsuoka",
                      skip_embeddings=False, skip_ari=False):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    runs = [load_run(rd) for rd in run_dirs]
    result = {"n_runs": len(runs), "exclusions": []}

    if len(runs) < 2:
        result["error"] = f"Need >= 2 runs, found {len(runs)}"
        return result

    # Layer 1: K distribution
    k_values = [len(r["skills"]) for r in runs]
    k_counts = Counter(k_values)
    modal_k, modal_count = k_counts.most_common(1)[0]
    result["k_layer"] = {
        "k_distribution": {str(k): k_counts[k] for k in sorted(k_counts)},
        "modal_k": modal_k,
        "modal_k_fraction": round(modal_count / len(runs), 4),
    }

    # Layer 2: codebook semantic matching (all runs with codebooks, any K)
    if skip_embeddings:
        result["codebook_layer"] = {"skipped": "embeddings disabled (--skip-embeddings)"}
    else:
        with_cb = [(r["run_id"], r["codebook"]) for r in runs if r["codebook"]]
        without_cb = [r["run_id"] for r in runs if not r["codebook"]]
        for run_id in without_cb:
            result["exclusions"].append(
                {"layer": "codebook", "run": run_id, "reason": "no codebook.json"})
        if len(with_cb) < 2:
            result["codebook_layer"] = {"skipped": f"only {len(with_cb)} run(s) have codebooks"}
        else:
            from src.embedding_client import EmbeddingClient
            client = EmbeddingClient()
            result["codebook_layer"] = codebook_stability(
                with_cb, client.embed_texts, out_dir / "embedding_cache.json")

    # Layers 3 and 4 operate on modal-K runs only (equal shapes required)
    modal_runs = [r for r in runs if len(r["skills"]) == modal_k]
    for r in runs:
        if len(r["skills"]) != modal_k:
            result["exclusions"].append({
                "layer": "matrix+classification", "run": r["run_id"],
                "reason": f"K={len(r['skills'])} != modal K={modal_k}",
            })

    # Layer 3: matrix stability
    if len(modal_runs) < 2:
        result["matrix_layer"] = {"skipped": f"only {len(modal_runs)} modal-K run(s)"}
    else:
        result["matrix_layer"] = compute_stability_from_matrices(
            [r["matrix"] for r in modal_runs])
        result["matrix_layer"]["runs_used"] = [r["run_id"] for r in modal_runs]

    # Layer 4: classification ARI
    if skip_ari:
        result["classification_layer"] = {"skipped": "ARI disabled (--skip-ari)"}
    elif len(modal_runs) < 2:
        result["classification_layer"] = {"skipped": f"only {len(modal_runs)} modal-K run(s)"}
    else:
        profile_paths, ari_runs = [], []
        for r in modal_runs:
            try:
                p = ari_mod.profiles_for(
                    Path(r["run_dir"]) / "Q.csv", dataset, out_dir / "profiles")
                profile_paths.append(p)
                ari_runs.append(r["run_id"])
            except RuntimeError as e:
                result["exclusions"].append(
                    {"layer": "classification", "run": r["run_id"], "reason": str(e)[:300]})
        if len(profile_paths) < 2:
            result["classification_layer"] = {
                "skipped": f"only {len(profile_paths)} run(s) produced profiles"}
        else:
            pw = ari_mod.pairwise_ari(profile_paths, out_dir / "pairwise_ari.json")
            aris = [p["ari"] for p in pw["pairs"]]
            result["classification_layer"] = {
                "mean_ari": round(statistics.mean(aris), 4),
                "min_ari": round(min(aris), 4),
                "sd_ari": round(statistics.stdev(aris), 4) if len(aris) > 1 else 0.0,
                "n_pairs": len(aris),
                "runs_used": ari_runs,
            }

    return result


def main():
    parser = argparse.ArgumentParser(description="Four-layer stability over contract run dirs.")
    parser.add_argument("--runs_root", required=True)
    parser.add_argument("--out", required=True, help="Output dir (caches + stability.json)")
    parser.add_argument("--dataset", default="tatsuoka")
    parser.add_argument("--skip-embeddings", action="store_true")
    parser.add_argument("--skip-ari", action="store_true")
    args = parser.parse_args()

    run_dirs = discover_runs(args.runs_root)
    result = compute_stability(run_dirs, args.out, dataset=args.dataset,
                               skip_embeddings=args.skip_embeddings,
                               skip_ari=args.skip_ari)
    out_path = Path(args.out) / "stability.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))
    print(f"Stability written to: {out_path}")


if __name__ == "__main__":
    main()
