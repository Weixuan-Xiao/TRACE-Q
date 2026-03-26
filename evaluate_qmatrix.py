"""Wrapper for R-based Q-matrix evaluation."""
import json
import subprocess
import tempfile
from pathlib import Path


def evaluate(qmatrix_csv: str, dataset: str = "tatsuoka") -> dict:
    """Evaluate a single Q-matrix via G-DINA. Returns dict with fit indices."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        output_path = f.name
    cmd = [
        "Rscript", str(Path(__file__).parent / "evaluate_qmatrix.R"),
        "--qmatrix", qmatrix_csv,
        "--dataset", dataset,
        "--output", output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": f"R script failed: {result.stderr}", "qmatrix_path": qmatrix_csv}
    with open(output_path) as f:
        return json.load(f)


def evaluate_batch(csv_paths: list[str], dataset: str = "tatsuoka") -> list[dict]:
    return [evaluate(p, dataset) for p in csv_paths]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python evaluate_qmatrix.py <qmatrix.csv> [dataset]")
        sys.exit(1)
    result = evaluate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "tatsuoka")
    print(json.dumps(result, indent=2))
