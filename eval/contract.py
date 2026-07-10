"""Run output contract: load, validate, and discover contract run directories.

A contract run directory contains:
  Q.csv         item_id + unique skill columns, strict 0/1 cells
  config.json   required: method, dataset, k_condition, k_selected, timestamp
  codebook.json optional: {"skills": [{skill_id, name, definition}, ...]}

See docs/evaluation_framework.md section 3.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_stability import load_qmatrix  # noqa: E402

REQUIRED_CONFIG_FIELDS = {"method", "dataset", "k_condition", "k_selected", "timestamp"}
_K_CONDITION_RE = re.compile(r"^(auto|fixed_\d+)$")


def load_run(run_dir):
    """Load a contract run directory -> dict with items/skills/matrix/config/codebook."""
    run_dir = Path(run_dir)
    items, skills, matrix = load_qmatrix(run_dir / "Q.csv")
    with open(run_dir / "config.json") as f:
        config = json.load(f)
    codebook = None
    codebook_path = run_dir / "codebook.json"
    if codebook_path.exists():
        with open(codebook_path) as f:
            codebook = json.load(f)
    return {
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "items": items,
        "skills": skills,
        "matrix": matrix,
        "config": config,
        "codebook": codebook,
    }


def validate_run(run_dir):
    """Validate a run directory against the contract. Returns list of violations (empty = valid)."""
    run_dir = Path(run_dir)
    violations = []

    q_path = run_dir / "Q.csv"
    config_path = run_dir / "config.json"
    if not q_path.exists():
        violations.append("missing Q.csv")
    if not config_path.exists():
        violations.append("missing config.json")
    if violations:
        return violations

    skills = None
    try:
        with open(q_path, newline="") as f:
            lines = f.read().splitlines()
        header = lines[0].split(",")
        if header[0] != "item_id":
            violations.append(f"Q.csv first column must be 'item_id', got '{header[0]}'")
        skills = header[1:]
        if len(skills) != len(set(skills)):
            violations.append("Q.csv has duplicate skill column names")
        if not skills:
            violations.append("Q.csv has no skill columns")
        for ln, line in enumerate(lines[1:], start=2):
            cells = line.split(",")[1:]
            for c in cells:
                if c.strip() not in ("0", "1"):
                    violations.append(f"Q.csv line {ln}: non-binary cell '{c.strip()}'")
                    break
    except Exception as e:
        violations.append(f"Q.csv unreadable: {e}")

    config = None
    try:
        with open(config_path) as f:
            config = json.load(f)
    except Exception as e:
        violations.append(f"config.json unreadable: {e}")

    if isinstance(config, dict):
        missing = REQUIRED_CONFIG_FIELDS - set(config)
        if missing:
            violations.append(f"config.json missing fields: {sorted(missing)}")
        k_condition = config.get("k_condition")
        if isinstance(k_condition, str) and not _K_CONDITION_RE.match(k_condition):
            violations.append(f"config.json k_condition must be 'auto' or 'fixed_<n>', got '{k_condition}'")
        k_selected = config.get("k_selected")
        if skills and isinstance(k_selected, int) and k_selected != len(skills):
            violations.append(
                f"config.json k_selected={k_selected} != {len(skills)} skill columns in Q.csv"
            )

    codebook_path = run_dir / "codebook.json"
    if codebook_path.exists() and skills:
        try:
            with open(codebook_path) as f:
                codebook = json.load(f)
            cb_skills = codebook.get("skills")
            if not isinstance(cb_skills, list):
                violations.append("codebook.json missing 'skills' list")
            else:
                cb_ids = [s.get("skill_id") for s in cb_skills]
                if set(cb_ids) != set(skills):
                    violations.append(
                        f"codebook.json skill_ids {sorted(filter(None, cb_ids))} != Q.csv columns {sorted(skills)}"
                    )
                for s in cb_skills:
                    if not s.get("name") or not s.get("definition"):
                        violations.append(f"codebook.json skill '{s.get('skill_id')}' missing name/definition")
                        break
        except Exception as e:
            violations.append(f"codebook.json unreadable: {e}")

    return violations


def discover_runs(runs_root):
    """Find contract run directories (containing Q.csv + config.json) under runs_root."""
    runs_root = Path(runs_root)
    if (runs_root / "Q.csv").exists() and (runs_root / "config.json").exists():
        return [runs_root]
    return sorted(
        d for d in runs_root.iterdir()
        if d.is_dir() and (d / "Q.csv").exists() and (d / "config.json").exists()
    )


def main():
    parser = argparse.ArgumentParser(description="Validate contract run directories.")
    parser.add_argument("path", help="A run directory or a root containing run directories")
    args = parser.parse_args()

    run_dirs = discover_runs(args.path)
    if not run_dirs:
        print(f"No contract run directories found under {args.path}")
        sys.exit(1)

    any_invalid = False
    for rd in run_dirs:
        violations = validate_run(rd)
        if violations:
            any_invalid = True
            print(f"INVALID {rd}")
            for v in violations:
                print(f"  - {v}")
        else:
            print(f"OK      {rd}")
    print(f"{len(run_dirs)} run dir(s) checked.")
    sys.exit(1 if any_invalid else 0)


if __name__ == "__main__":
    main()
