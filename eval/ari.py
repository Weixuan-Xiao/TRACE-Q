"""Classification-level ARI between Q-matrices (dimension E2 / stability layer 4).

Fits GDINA once per Q (cached by content hash), then computes pairwise
Adjusted Rand Index over the resulting student MAP profiles.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

_EVAL_DIR = Path(__file__).resolve().parent


def _sha1_of_file(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


def profiles_for(q_csv, dataset, cache_dir):
    """Extract (or reuse cached) MAP profiles for one Q-matrix. Returns profile CSV path."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = f"{_sha1_of_file(q_csv)}_{dataset}"
    out_path = cache_dir / f"profiles_{key}.csv"
    if out_path.exists():
        return out_path
    cmd = [
        "Rscript", str(_EVAL_DIR / "extract_profiles.R"),
        "--qmatrix", str(q_csv), "--dataset", dataset, "--output", str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out_path.exists():
        raise RuntimeError(
            f"profile extraction failed for {q_csv}: {proc.stdout} {proc.stderr}"
        )
    return out_path


def pairwise_ari(profile_paths, output_path):
    """Compute pairwise ARI over profile CSVs in one Rscript call. Returns parsed dict."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "Rscript", str(_EVAL_DIR / "pairwise_ari.R"),
        "--output", str(output_path),
        "--profiles", *[str(p) for p in profile_paths],
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not output_path.exists():
        raise RuntimeError(f"pairwise ARI failed: {proc.stdout} {proc.stderr}")
    with open(output_path) as f:
        return json.load(f)


def ari_between(q_csv_a, q_csv_b, dataset, cache_dir):
    """Convenience: ARI between two Q-matrices' classifications."""
    pa = profiles_for(q_csv_a, dataset, cache_dir)
    pb = profiles_for(q_csv_b, dataset, cache_dir)
    result = pairwise_ari([pa, pb], Path(cache_dir) / "ari_pair.json")
    return result["pairs"][0]["ari"]


def main():
    parser = argparse.ArgumentParser(description="Classification ARI between two Q-matrices.")
    parser.add_argument("--qmatrix_a", required=True)
    parser.add_argument("--qmatrix_b", required=True)
    parser.add_argument("--dataset", default="tatsuoka")
    parser.add_argument("--cache_dir", default="eval_out/profiles")
    args = parser.parse_args()

    ari = ari_between(args.qmatrix_a, args.qmatrix_b, args.dataset, args.cache_dir)
    print(json.dumps({
        "qmatrix_a": args.qmatrix_a,
        "qmatrix_b": args.qmatrix_b,
        "dataset": args.dataset,
        "ari": ari,
    }, indent=2))


if __name__ == "__main__":
    main()
