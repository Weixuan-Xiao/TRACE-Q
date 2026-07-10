"""Convert legacy experiment run directories to contract run directories.

Legacy layout: <experiment>/run*/step6_Q_matrix_K{k}.csv (fallback: step8
auditor reviewed CSV), step3_skill_codebook.json, run_meta.json/run_config.json.
"""
import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_stability import load_qmatrix  # noqa: E402
from eval.contract import validate_run  # noqa: E402


def _write_canonical_q(items, skills, matrix, out_path):
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id"] + list(skills))
        for item_id, row in zip(items, matrix):
            writer.writerow([item_id] + list(row))


def convert_run(run_dir, k, out_dir, method, dataset):
    """Convert one legacy run dir. Returns list of contract violations (empty = ok)."""
    run_dir = Path(run_dir)
    q_path = run_dir / f"step6_Q_matrix_K{k}.csv"
    q_source = "step6"
    if not q_path.exists():
        q_path = run_dir / f"step8_auditor_Q_matrix_K{k}_reviewed.csv"
        q_source = "step8"
    if not q_path.exists():
        return [f"no Q-matrix CSV for K={k} in {run_dir}"]

    items, skills, matrix = load_qmatrix(q_path)

    meta = {}
    for name in ("run_meta.json", "run_config.json"):
        p = run_dir / name
        if p.exists():
            with open(p) as f:
                meta.update(json.load(f))

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_canonical_q(items, skills, matrix, out_dir / "Q.csv")

    codebook_path = run_dir / "step3_skill_codebook.json"
    if codebook_path.exists():
        shutil.copy(codebook_path, out_dir / "codebook.json")

    config = {
        "method": method,
        "dataset": dataset,
        "k_condition": f"fixed_{k}" if meta.get("target_k_exact") else "auto",
        "k_selected": len(skills),
        "timestamp": meta.get("created_at") or meta.get("timestamp") or "",
        "method_version": meta.get("prompt_version"),
        "model": meta.get("model"),
        "seed": meta.get("seed"),
        "token_cost": None,
        "source": {"legacy_path": str(run_dir), "qmatrix_file": q_path.name, "stage": q_source},
    }
    with open(out_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    return validate_run(out_dir)


def main():
    parser = argparse.ArgumentParser(description="Convert legacy experiment runs to contract format.")
    parser.add_argument("--experiment", required=True, help="Legacy experiment dir containing run1/, run2/, ...")
    parser.add_argument("--k", type=int, required=True, help="K value of Q-matrix CSVs to convert")
    parser.add_argument("--out", required=True, help="Output runs root")
    parser.add_argument("--method", default=None, help="Method name for config.json (default: experiment dir name)")
    parser.add_argument("--dataset", default="tatsuoka")
    args = parser.parse_args()

    experiment = Path(args.experiment)
    method = args.method or experiment.name
    run_dirs = sorted(
        [d for d in experiment.iterdir() if d.is_dir() and d.name.startswith("run")],
        key=lambda p: int(p.name.removeprefix("run")),
    )
    if not run_dirs:
        print(f"No run*/ directories under {experiment}")
        sys.exit(1)

    n_ok, n_fail = 0, 0
    for rd in run_dirs:
        out_dir = Path(args.out) / f"{method}_{rd.name}"
        violations = convert_run(rd, args.k, out_dir, method, args.dataset)
        if violations:
            n_fail += 1
            print(f"FAILED  {rd} -> {out_dir}")
            for v in violations:
                print(f"  - {v}")
        else:
            n_ok += 1
            print(f"OK      {rd} -> {out_dir}")

    print(f"Converted {n_ok} run(s), {n_fail} failure(s).")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
