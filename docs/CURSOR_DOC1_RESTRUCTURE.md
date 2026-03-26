# Document 1: Project Restructuring

## What This Document Covers

Four essential changes to the TRACE-Q pipeline, in priority order:

1. **Automated Q-matrix evaluation** — integrate R-based G-DINA model fit into the workflow
2. **Stability metrics** — compute element-wise agreement and Fleiss' κ across repeated runs
3. **Fix K** — add `--target_k_exact` flag so we only produce one Q-matrix at a chosen K
4. **Parameterize the pipeline** — make voting rules, tagger count, model, and stage skipping configurable via CLI flags

**Rule: Do NOT break backward compatibility.** `python pipeline.py all` with no extra arguments must produce identical results to the current version.

---

## Codebase Orientation

Read these files before making any changes:

| File | What It Does | Hardcoded Values You'll Touch |
|------|-------------|-------------------------------|
| `pipeline.py` | Orchestrator. Calls each step via `subprocess.check_call`. | Already has `--outputs_dir`, `--prompts_dir`, `--input`, `--target_k`. |
| `run_experiments.py` | Runs `pipeline.py` N times → `outputs_exp/{version}/run{i}/`. | Propagates flags to `pipeline.py`. |
| `main_taxonomist.py` | Step 3: Expert Committee + Supervisor → codebook. | `expert_ids = ["A", "B", "C"]` (line 99). |
| `main_taggers.py` | Step 4: 5 taggers annotate items. | `tagger_ids = ["T1", "T2", "T3", "T4", "T5"]` (line 80). |
| `main_judge.py` | Step 5: Skill-level voting + Judge adjudication. | `count >= 4` auto-include (line 75), `count <= 1` auto-exclude (line 77). `v1..v5 = load_votes(...)` hardcoded (lines 172-176). `votes_bundle = {"T1":..., "T5":...}` (lines 203-206). |
| `src/llm_client.py` | OpenAI API wrapper. `LLMConfig` dataclass. | Reads `OPENAI_API_KEY`, `OPENAI_MODEL` from env. `chat_completions()` already accepts `model` override. |
| `src/expert.py` | Expert agent. | `__init__` takes `prompt_path` only (no `prompt_text`). |
| `src/supervisor.py` | SupervisorAlign + SupervisorConsolidate. | `align()` takes `codebook_a`, `codebook_b`, `codebook_c` separately. `_validate_skill_count()` enforces 3-8 range. |
| `schemas/supervisor_align_output.py` | Pydantic schema for alignment. | `expert_a_skill_ids`, `expert_b_skill_ids`, `expert_c_skill_ids` as separate fields. `consensus` pattern: `^[123]/3$`. **Do NOT change this schema.** |
| `schemas/tagger_vote.py` | `SkillTag`: `skill_id`, `evidence_step_ids`, `reasoning`. | No `confidence` field (not needed now). |
| `analyze_stability.py` | Cross-run metrics. | Has `_fleiss_kappa()`, `_cohens_kappa()`, element-wise agreement. Can reuse these functions. |
| `Analysis.R` | Current R evaluation. Manual, hardcoded paths. | Uses `GDINA` package. Will be replaced by `evaluate_qmatrix.R`. |

---

## Task 1: Automated Q-Matrix Evaluation

### 1A: Create `evaluate_qmatrix.R`

Callable from command line:
```bash
Rscript evaluate_qmatrix.R --qmatrix path/to/Q.csv --dataset tatsuoka --output results.json
```

**Implementation:**

```r
# evaluate_qmatrix.R
# Usage: Rscript evaluate_qmatrix.R --qmatrix <path> --dataset <name> --output <path>

library(GDINA)

# --- Parse arguments ---
args <- commandArgs(trailingOnly = TRUE)
qmatrix_path <- NULL
dataset <- "tatsuoka"
output_path <- "eval_result.json"

i <- 1
while (i <= length(args)) {
  if (args[i] == "--qmatrix") { qmatrix_path <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--dataset") { dataset <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--output") { output_path <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

if (is.null(qmatrix_path)) stop("--qmatrix is required")

# --- Load response data ---
if (dataset == "tatsuoka") {
  data <- GDINA::realdata_Tatsuoka1990$dat
} else {
  data <- read.csv(dataset)
}

# --- Load Q-matrix ---
Q_raw <- read.csv(qmatrix_path)
Q <- Q_raw[, -1]  # Drop item_id column
Q[] <- lapply(Q, function(x) as.integer(gsub("[^01]", "", as.character(x))))
Q <- as.matrix(Q)

N <- nrow(data)
n_items <- nrow(Q)
n_skills <- ncol(Q)

# --- Fit G-DINA and extract metrics ---
result_list <- list(
  qmatrix_path = qmatrix_path,
  dataset = dataset,
  n_items = n_items,
  n_skills = n_skills,
  AIC = NULL, BIC = NULL, CAIC = NULL, SABIC = NULL,
  RMSEA2 = NULL, SRMSR = NULL,
  log_likelihood = NULL, n_params = NULL,
  converged = NULL, error = NULL
)

tryCatch({
  set.seed(1)
  fit <- GDINA::GDINA(data, Q)
  
  ll <- as.numeric(logLik(fit))
  npar <- fit@npar  # or extract from summary
  
  result_list$AIC <- AIC(fit)
  result_list$BIC <- BIC(fit)
  result_list$CAIC <- -2 * ll + npar * (log(N) + 1)
  result_list$SABIC <- -2 * ll + npar * log((N + 2) / 24)
  result_list$log_likelihood <- ll
  result_list$n_params <- npar
  result_list$converged <- TRUE
  
  tryCatch({
    mf <- GDINA::modelfit(fit)
    # modelfit returns a list; check structure with str(mf)
    result_list$RMSEA2 <- mf$RMSEA2
    result_list$SRMSR <- mf$SRMSR
  }, error = function(e) {
    # RMSEA2/SRMSR may be unavailable for complex models
    result_list$RMSEA2 <<- NULL
    result_list$SRMSR <<- NULL
  })
  
}, error = function(e) {
  result_list$converged <<- FALSE
  result_list$error <<- conditionMessage(e)
})

# --- Write JSON ---
library(jsonlite)
json_str <- toJSON(result_list, auto_unbox = TRUE, pretty = TRUE, null = "null")
writeLines(json_str, output_path)
cat("Evaluation written to:", output_path, "\n")
```

**Notes for Cursor:**
- `fit@npar` — check if this is the right accessor. It might be `extract(fit, "npar")` or from `summary(fit)`. Inspect the GDINA object structure.
- `mf$RMSEA2` and `mf$SRMSR` — check `str(mf)` to find the exact field names. They might be nested differently.
- The `realdata_Tatsuoka1990` dataset has 536 examinees and 20 items.

### 1B: Create `evaluate_qmatrix.py`

Python wrapper:

```python
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
```

### Test after creating both files:
```bash
Rscript evaluate_qmatrix.R \
  --qmatrix outputs_exp/v2/run1/step6_Q_matrix_K5.csv \
  --dataset tatsuoka \
  --output test_eval.json
cat test_eval.json
```

---

## Task 2: Stability Metrics

### 2A: Create `evaluate_stability.py`

Computes two stability metrics across N repeated runs:

- **Element-wise agreement rate**: Average proportion of runs that agree with the majority vote, across all cells.
- **Fleiss' κ**: Multi-rater reliability treating each run as a rater and each Q-matrix cell as a subject.

```bash
python evaluate_stability.py --run_dir outputs_exp/v2 --k 5 --output stability.json
```

**Implementation — reuse logic from `analyze_stability.py`:**

The existing `analyze_stability.py` already computes both metrics (element-wise agreement at lines 181-208, Fleiss' κ at lines 57-90). Extract these into reusable functions.

```python
"""Stability metrics for Q-matrices across repeated runs."""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path


def load_qmatrix(csv_path):
    """Load Q-matrix CSV → (item_ids, skill_ids, matrix[row][col])."""
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        skill_cols = [h for h in header[1:] if h.startswith("S")]
        n_skills = len(skill_cols)
        items, rows = [], []
        for row in reader:
            items.append(row[0])
            # Handle auditor "*" markers
            rows.append([int(row[1 + c].replace("*", "").strip()) for c in range(n_skills)])
    return items, skill_cols, rows


def fleiss_kappa(all_matrices, n_runs):
    """Fleiss' kappa: each run = a rater, each cell = a subject."""
    n_items = len(all_matrices[0])
    n_skills = len(all_matrices[0][0])
    N = n_items * n_skills

    count_1 = [0] * N
    for mat in all_matrices:
        idx = 0
        for i in range(n_items):
            for j in range(n_skills):
                count_1[idx] += mat[i][j]
                idx += 1

    sum_Pi = 0.0
    for s in range(N):
        c1 = count_1[s]
        c0 = n_runs - c1
        sum_Pi += (c0 * (c0 - 1) + c1 * (c1 - 1)) / (n_runs * (n_runs - 1))
    P_bar = sum_Pi / N

    total = N * n_runs
    p1 = sum(count_1) / total
    p0 = 1 - p1
    P_e = p0 * p0 + p1 * p1

    if P_e >= 1.0:
        return 1.0
    return (P_bar - P_e) / (1 - P_e)


def element_wise_agreement(all_matrices, n_runs):
    """Average cell-level agreement with majority vote."""
    n_items = len(all_matrices[0])
    n_skills = len(all_matrices[0][0])
    total_agreement = 0.0
    total_cells = n_items * n_skills

    for i in range(n_items):
        for j in range(n_skills):
            ones = sum(mat[i][j] for mat in all_matrices)
            majority_count = max(ones, n_runs - ones)
            total_agreement += majority_count / n_runs

    return total_agreement / total_cells


def compute_stability_metrics(run_dir: str, k: int) -> dict:
    """
    Compute stability metrics across all runs in a directory.
    
    Expects: run_dir/run1/step6_Q_matrix_K{k}.csv, run_dir/run2/..., etc.
    Falls back to step8_auditor_Q_matrix_K{k}_reviewed.csv if step6 not found.
    """
    run_dir = Path(run_dir)
    run_dirs = sorted(
        [d for d in run_dir.iterdir() if d.is_dir() and d.name.startswith("run")],
        key=lambda p: int(p.name.removeprefix("run")),
    )

    # Load all Q-matrices
    all_matrices = []
    for rd in run_dirs:
        qm_path = rd / f"step6_Q_matrix_K{k}.csv"
        if not qm_path.exists():
            qm_path = rd / f"step8_auditor_Q_matrix_K{k}_reviewed.csv"
        if qm_path.exists():
            _, _, matrix = load_qmatrix(qm_path)
            all_matrices.append(matrix)

    n_runs = len(all_matrices)
    if n_runs < 2:
        return {"error": f"Need >= 2 runs, found {n_runs}", "n_runs": n_runs}

    n_items = len(all_matrices[0])
    n_skills = len(all_matrices[0][0])

    # Count unique Q-matrices
    q_strings = [str(mat) for mat in all_matrices]
    unique_counts = Counter(q_strings)
    n_unique = len(unique_counts)
    modal_freq = unique_counts.most_common(1)[0][1]

    return {
        "run_dir": str(run_dir),
        "k": k,
        "n_runs": n_runs,
        "n_items": n_items,
        "n_skills": n_skills,
        "total_cells": n_items * n_skills,
        "element_wise_agreement": round(element_wise_agreement(all_matrices, n_runs), 4),
        "fleiss_kappa": round(fleiss_kappa(all_matrices, n_runs), 4),
        "n_unique_qmatrices": n_unique,
        "modal_qmatrix_frequency": modal_freq,
        "modal_qmatrix_frequency_pct": round(modal_freq / n_runs, 4),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute stability metrics across runs.")
    parser.add_argument("--run_dir", required=True, help="Directory containing run1/, run2/, ...")
    parser.add_argument("--k", type=int, required=True, help="K value of Q-matrices to analyze")
    parser.add_argument("--output", default=None, help="Output JSON path (default: print to stdout)")
    args = parser.parse_args()

    result = compute_stability_metrics(args.run_dir, args.k)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Stability metrics written to: {args.output}")
    else:
        print(json.dumps(result, indent=2))
```

### 2B: Create `evaluate_experiment.py`

Master script combining quality (mean ± SD of fit indices) and stability:

```bash
python evaluate_experiment.py --run_dir outputs_exp/v2 --k 5 --dataset tatsuoka --output report.json
```

```python
"""Master evaluation: quality (G-DINA fit) + stability across runs."""
import argparse
import json
import statistics
from pathlib import Path

from evaluate_qmatrix import evaluate as eval_quality
from evaluate_stability import compute_stability_metrics


def evaluate_experiment(run_dir: str, k: int, dataset: str = "tatsuoka") -> dict:
    """Run quality + stability evaluation on a set of repeated runs."""
    run_dir = Path(run_dir)
    run_dirs = sorted(
        [d for d in run_dir.iterdir() if d.is_dir() and d.name.startswith("run")],
        key=lambda p: int(p.name.removeprefix("run")),
    )

    # --- Quality: evaluate each run's Q-matrix ---
    quality_results = []
    for rd in run_dirs:
        qm_path = rd / f"step6_Q_matrix_K{k}.csv"
        if not qm_path.exists():
            qm_path = rd / f"step8_auditor_Q_matrix_K{k}_reviewed.csv"
        if qm_path.exists():
            q_eval = eval_quality(str(qm_path), dataset)
            if q_eval.get("error") is None:
                quality_results.append(q_eval)

    # Aggregate quality metrics: mean ± SD
    quality_summary = {}
    for metric in ["AIC", "BIC", "CAIC", "SABIC", "RMSEA2", "SRMSR"]:
        values = [r[metric] for r in quality_results if r.get(metric) is not None]
        if values:
            quality_summary[metric] = {
                "mean": round(statistics.mean(values), 4),
                "sd": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "n": len(values),
            }

    # --- Stability ---
    stability = compute_stability_metrics(str(run_dir), k)

    return {
        "config": {
            "run_dir": str(run_dir),
            "k": k,
            "dataset": dataset,
            "n_runs_evaluated": len(quality_results),
        },
        "quality": quality_summary,
        "stability": stability,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--dataset", default="tatsuoka")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    result = evaluate_experiment(args.run_dir, args.k, args.dataset)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Report written to: {args.output}")
    else:
        print(json.dumps(result, indent=2))
```

### Test after creating both:
```bash
# Test stability alone (existing 10-run data)
python evaluate_stability.py --run_dir outputs_exp/v2 --k 5

# Test full experiment evaluation
python evaluate_experiment.py --run_dir outputs_exp/v2 --k 5 --dataset tatsuoka
```

The output of `evaluate_experiment.py` is the **standard report format** for every experiment going forward.

---

## Task 3: Fix K with `--target_k_exact`

### How It Works

When `--target_k_exact 4` is set:
1. **Expert prompt** changes from "between 3 and 8 skills" → "exactly 4 skills"
2. **Supervisor validation** changes from 3-8 range → exactly 4
3. **Aggregator step is skipped** (no need to merge — already at target K)
4. **Export + Audit** only handle one K level

This constrains the pipeline to produce exactly one Q-matrix at K=4.

### 3A: Modify `src/expert.py`

Allow accepting prompt as text (not just file path):

```python
# Current __init__:
def __init__(self, llm, expert_id, prompt_path="prompts/v2/expert.txt"):
    base_prompt = load_text(prompt_path)
    self._system_prompt = f'You are Expert "{expert_id}".\n\n{base_prompt}'

# New __init__ — add prompt_text parameter:
def __init__(self, llm, expert_id, prompt_path=None, prompt_text=None):
    if prompt_text is not None:
        base_prompt = prompt_text
    elif prompt_path is not None:
        base_prompt = load_text(prompt_path)
    else:
        raise ValueError("Either prompt_path or prompt_text must be provided")
    self._system_prompt = f'You are Expert "{expert_id}".\n\n{base_prompt}'
```

### 3B: Modify `main_taxonomist.py`

Add CLI argument:
```python
parser.add_argument(
    "--target_k_exact", type=int, default=None,
    help="Constrain experts to produce exactly this many skills.",
)
```

When set, modify prompt text before creating experts:
```python
from src.agent_utils import load_text

# After parsing args, before running experts:
expert_prompt_path = str(Path(args.prompts_dir) / "expert.txt")

if args.target_k_exact:
    k = args.target_k_exact
    expert_prompt_text = load_text(expert_prompt_path)
    # Replace skill count constraints (these exact strings are in prompts/v2/expert.txt)
    expert_prompt_text = expert_prompt_text.replace(
        "between 3 and 8 skills (inclusive)",
        f"exactly {k} skills"
    ).replace(
        "No fewer than 3, no more than 8",
        f"Exactly {k} — no more, no fewer"
    ).replace(
        "You MUST define between 3 and 8 skills",
        f"You MUST define exactly {k} skills"
    )
else:
    expert_prompt_text = None  # Use file path as before
```

Then in the `run_expert()` function and the expert creation calls, pass either `prompt_text` or `prompt_path`:
```python
def run_expert(expert_id, verified_dossiers, prompts_dir, prompt_text=None):
    llm = LLMClient()
    if prompt_text is not None:
        expert = Expert(llm=llm, expert_id=expert_id, prompt_text=prompt_text)
    else:
        expert = Expert(llm=llm, expert_id=expert_id,
                       prompt_path=str(Path(prompts_dir) / "expert.txt"))
    codebook = expert.build_codebook(verified_dossiers=verified_dossiers)
    return {"expert_id": expert_id, "codebook": codebook}
```

### 3C: Modify `src/supervisor.py` — `SupervisorConsolidate`

The `_validate_skill_count` method currently enforces 3-8. Add an optional `target_k_exact` parameter:

```python
class SupervisorConsolidate:
    def __init__(self, llm, prompt_path=..., target_k_exact=None):
        # ... existing init ...
        self.target_k_exact = target_k_exact
    
    def _validate_skill_count(self, output):
        skills = output.get("final_codebook", {}).get("skills", [])
        n = len(skills)
        
        if self.target_k_exact:
            if n != self.target_k_exact:
                return f"Expected exactly {self.target_k_exact} skills, got {n}."
        else:
            if n < 3:
                return f"Too few skills ({n}). Must have at least 3."
            if n > 8:
                return f"Too many skills ({n}). Must have at most 8."
        
        # ... rest of existing validation (duplicate skill_id check) ...
```

Also modify the consolidation prompt dynamically in `main_taxonomist.py` when `target_k_exact` is set — same string replacement approach:
```python
if args.target_k_exact:
    # Also modify supervisor consolidate prompt
    consolidate_prompt_path = str(Path(args.prompts_dir) / "supervisor_consolidate.txt")
    consolidate_prompt_text = load_text(consolidate_prompt_path)
    consolidate_prompt_text = consolidate_prompt_text.replace(
        "3-8 skills", f"exactly {args.target_k_exact} skills"
    ).replace(
        "MUST have exactly 3-8 skills", f"MUST have exactly {args.target_k_exact} skills"
    )
    # Pass to SupervisorConsolidate similarly (add prompt_text param)
```

### 3D: Modify `pipeline.py`

```python
parser.add_argument(
    "--target_k_exact", type=int, default=None,
    help="Fix K: experts produce exactly this many skills. Skips Aggregator.",
)
```

Pass to `main_taxonomist.py`:
```python
if args.cmd in ("codebook", "all"):
    codebook_cmd = base + [
        "main_taxonomist.py",
        "--input", str(outputs_dir / "step2_verifier_verified_item_dossiers.jsonl"),
        "--out", str(outputs_dir / "step3_skill_codebook.json"),
        "--out_experts", str(outputs_dir / "step3_expert_codebooks.json"),
        "--out_align", str(outputs_dir / "step3_supervisor_align_output.json"),
        "--out_supervisor", str(outputs_dir / "step3_supervisor_output.json"),
        "--prompts_dir", prompts_dir,
    ]
    if args.target_k_exact:
        codebook_cmd.extend(["--target_k_exact", str(args.target_k_exact)])
    run(codebook_cmd)
```

Skip Aggregator:
```python
if args.cmd in ("aggregate", "all"):
    if args.target_k_exact:
        print(f"Skipping aggregation: --target_k_exact={args.target_k_exact}")
    else:
        target_k_str = resolve_target_k()
        if target_k_str:
            run(base + ["main_aggregator.py", ...])
```

Audit only the single K:
```python
if args.cmd in ("audit", "all"):
    if args.target_k_exact:
        all_k = [args.target_k_exact]
    else:
        all_k = get_all_k_values()
    # ... existing audit loop over all_k ...
```

### 3E: Propagate through `run_experiments.py`

```python
parser.add_argument("--target_k_exact", type=int, default=None)
# In run loop:
if args.target_k_exact:
    cmd_args.extend(["--target_k_exact", str(args.target_k_exact)])
```

### Test:
```bash
python pipeline.py --target_k_exact 4 all
# Should produce: step3 codebook with exactly 4 skills, step6_Q_matrix_K4.csv, no aggregated versions
```

---

## Task 4: Parameterize the Pipeline

### 4A: Configurable voting — modify `main_judge.py`

**Add CLI arguments:**
```python
parser.add_argument("--include_threshold", type=int, default=4)
parser.add_argument("--exclude_threshold", type=int, default=1)
parser.add_argument("--consensus_mode", default="threshold",
    choices=["threshold", "majority", "unanimity"])
```

**Modify `compute_skill_level_votes()`** — change signature to accept thresholds:
```python
def compute_skill_level_votes(votes_by_tagger, include_threshold=4, exclude_threshold=1):
    # ... existing logic, but replace:
    #   count >= 4  →  count >= include_threshold
    #   count <= 1  →  count <= exclude_threshold
```

**Add two new functions:**
```python
def compute_majority_votes(votes_by_tagger):
    """Include if > 50% of taggers agree."""
    n_taggers = len(votes_by_tagger)
    threshold = n_taggers / 2
    skill_counts = {}
    for _tid, vote in votes_by_tagger.items():
        for sid in skill_set(vote):
            skill_counts[sid] = skill_counts.get(sid, 0) + 1
    return {
        "skill_counts": skill_counts,
        "auto_include": sorted(s for s, c in skill_counts.items() if c > threshold),
        "auto_exclude": sorted(s for s, c in skill_counts.items() if c <= threshold),
        "disputed": [],
        "has_disputed": False,
        "n_taggers": n_taggers,
    }

def compute_unanimity_votes(votes_by_tagger):
    """Include only if ALL taggers agree."""
    n_taggers = len(votes_by_tagger)
    skill_counts = {}
    for _tid, vote in votes_by_tagger.items():
        for sid in skill_set(vote):
            skill_counts[sid] = skill_counts.get(sid, 0) + 1
    return {
        "skill_counts": skill_counts,
        "auto_include": sorted(s for s, c in skill_counts.items() if c == n_taggers),
        "auto_exclude": sorted(s for s, c in skill_counts.items() if c < n_taggers),
        "disputed": [],
        "has_disputed": False,
        "n_taggers": n_taggers,
    }
```

**Dispatch in main loop** — replace `vote_stats = compute_skill_level_votes(votes_bundle)` with:
```python
if args.consensus_mode == "majority":
    vote_stats = compute_majority_votes(votes_bundle)
elif args.consensus_mode == "unanimity":
    vote_stats = compute_unanimity_votes(votes_bundle)
else:
    vote_stats = compute_skill_level_votes(
        votes_bundle, args.include_threshold, args.exclude_threshold)
```

### 4B: Dynamic tagger discovery — modify `main_judge.py`

Replace hardcoded `v1..v5 = load_votes(...)` (lines 172-176) with:
```python
vote_files = sorted(Path(args.votes_dir).glob("T*.jsonl"))
if not vote_files:
    raise RuntimeError(f"No tagger vote files found in {args.votes_dir}")
all_votes = {}
for vf in vote_files:
    all_votes[vf.stem] = load_votes(str(vf))
print(f"Loaded {len(all_votes)} tagger files: {sorted(all_votes.keys())}")
```

Replace hardcoded `votes_bundle = {"T1": vote_T1, ...}` (lines 203-206) with:
```python
votes_bundle = {}
for tid, votes_map in all_votes.items():
    v = votes_map.get(item_id)
    if v is None:
        raise RuntimeError(f"Missing vote for {item_id} from {tid}")
    votes_bundle[tid] = v
```

### 4C: Dynamic tagger count — modify `main_taggers.py`

```python
parser.add_argument("--n_taggers", type=int, default=5)
```

Replace `tagger_ids = ["T1", "T2", "T3", "T4", "T5"]` with:
```python
tagger_ids = [f"T{i+1}" for i in range(args.n_taggers)]
```

Update ThreadPoolExecutor:
```python
with ThreadPoolExecutor(max_workers=args.n_taggers) as executor:
```

### 4D: Model override — modify `pipeline.py`

```python
parser.add_argument("--model", default=None,
    help="Override LLM model for all stages.")
```

Modify `run()`:
```python
def run(cmd, extra_env=None):
    print(">>>", " ".join(cmd))
    env = None
    if extra_env:
        import os
        env = os.environ.copy()
        env.update(extra_env)
    subprocess.check_call(cmd, env=env)
```

Use everywhere:
```python
env_overrides = {}
if args.model:
    env_overrides["OPENAI_MODEL"] = args.model
# Pass to every run() call:
run(some_cmd, extra_env=env_overrides or None)
```

### 4E: Skip stages — modify `pipeline.py`

```python
parser.add_argument("--skip_stages", default="",
    help="Comma-separated: verifier,auditor")
```

```python
skip = set(s.strip() for s in args.skip_stages.split(",") if s.strip())
allowed = {"verifier", "auditor"}
invalid = skip - allowed
if invalid:
    parser.error(f"Cannot skip: {invalid}. Only {allowed} allowed.")
```

When verifier is skipped, copy step1 → step2:
```python
if "verifier" in skip:
    shutil.copy2(
        outputs_dir / "step1_solver_item_dossiers.jsonl",
        outputs_dir / "step2_verifier_verified_item_dossiers.jsonl")
    print("SKIPPED verifier")
```

### 4F: Propagate ALL new flags through `pipeline.py` → `run_experiments.py`

In `pipeline.py`, pass new args to each step's subprocess call.
In `run_experiments.py`, add matching arguments and forward to `pipeline.py`.

### 4G: Run logging — modify `pipeline.py`

At end of `all` command, write `run_config.json`:
```python
run_config = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "model": args.model or os.getenv("OPENAI_MODEL", ""),
    "prompts_dir": args.prompts_dir,
    "target_k_exact": args.target_k_exact,
    "n_taggers": args.n_taggers,
    "consensus_mode": args.consensus_mode,
    "include_threshold": args.include_threshold,
    "exclude_threshold": args.exclude_threshold,
    "skip_stages": args.skip_stages,
    "input": args.input,
}
(outputs_dir / "run_config.json").write_text(json.dumps(run_config, indent=2))
```

---

## Final State After All Tasks

```bash
# Full pipeline with all defaults (backward compatible):
python pipeline.py all

# Fixed K=4, custom config:
python pipeline.py --target_k_exact 4 --n_taggers 5 --consensus_mode majority --model gpt-4o all

# 20 repeated runs for stability:
python run_experiments.py --prompt_version v2 --runs 20 --target_k_exact 4

# Evaluate everything (quality + stability):
python evaluate_experiment.py --run_dir outputs_exp/v2 --k 4 --dataset tatsuoka --output report.json
```

---

## Implementation Order

1. **Task 1A-1B**: `evaluate_qmatrix.R` + `.py` → test with existing outputs
2. **Task 2A-2B**: `evaluate_stability.py` + `evaluate_experiment.py` → test with existing runs
3. **Task 3**: `--target_k_exact` → test: `python pipeline.py --target_k_exact 4 all`
4. **Task 4A-4B**: Voting + dynamic tagger loading → test: re-run judge with `--consensus_mode majority`
5. **Task 4C**: `--n_taggers` → test: `python pipeline.py --n_taggers 3 all`
6. **Task 4D-4E**: `--model` + `--skip_stages` → test each
7. **Task 4F-4G**: Flag propagation + run logging

## What NOT to Change

- **Expert count stays at 3.** SupervisorAlign schema is too tightly coupled to change safely.
- **No multi-provider LLM.** OpenAI-only for now. `--model` switches between OpenAI models (gpt-4o-mini, gpt-4o).
- **No debate/Delphi consensus.** Threshold/majority/unanimity cover the paper's needs.
