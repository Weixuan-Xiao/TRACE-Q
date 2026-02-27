# TRACE-Q Experiment Infrastructure — Implementation Specification

## Context for Cursor

You are modifying the TRACE-Q project, a multi-agent LLM pipeline that constructs Q-matrices for Cognitive Diagnostic Models (CDM). The project is a Python codebase that uses OpenAI's API to run multiple LLM agents in sequence, producing a binary items × skills matrix.

**The research goal:** We need to systematically test different pipeline configurations (consensus mechanisms, backbone LLMs, committee sizes, stage removal) to find the best-performing pipeline, then report results. This requires building experiment infrastructure that automates evaluation.

**Important:** Do NOT change any existing functionality or break backward compatibility. All changes should be additive — new flags, new files, new modules. The existing `python pipeline.py all` command must continue to work exactly as before.

---

## Current Architecture Summary

### File Structure
```
pipeline.py              — Main orchestrator, calls each step via subprocess
run_experiments.py       — Runs pipeline.py N times for stability analysis
analyze_stability.py     — Computes cross-run agreement metrics
main.py                  — Step 1: Solver (generates solutions)
main_verify.py           — Step 2: Verifier (checks solutions)
main_taxonomist.py       — Step 3: Expert Committee (3 experts) + Supervisor (align → consolidate) → codebook
main_taggers.py          — Step 4: 5 Taggers annotate items independently
main_judge.py            — Step 5: Judge adjudicates via skill-level voting
main_aggregator.py       — Step 6: Merges skills for lower-K variants
main_export_q.py         — Step 7: Exports Q-matrix CSV + reliability report
main_auditor.py          — Step 8: Auditor reviews final Q-matrix
src/llm_client.py        — OpenAI API wrapper (LLMClient class, LLMConfig dataclass)
src/agent_utils.py       — call_json_with_validation() — central LLM call + Pydantic validation + retry
src/expert.py            — Expert agent class
src/supervisor.py        — SupervisorAlign + SupervisorConsolidate classes
src/tagger.py            — Tagger agent class
src/judge.py             — Judge agent class
src/auditor.py           — Auditor agent class
src/aggregator.py        — Aggregator agent class
schemas/                 — Pydantic output schemas for each agent
prompts/v1/, prompts/v2/ — Prompt text files for each agent
data/items.jsonl         — Input items (currently: Tatsuoka fraction-subtraction, 20 items)
Analysis.R               — R script for G-DINA model fit comparison
```

### How LLM Calls Work
All LLM calls go through `src/llm_client.py`:
- `LLMClient` reads `OPENAI_API_KEY` and `OPENAI_MODEL` from `.env`
- `LLMConfig` dataclass holds `api_key`, `model`, `seed`
- `chat_completions()` method accepts `model` override parameter (already exists but unused by callers)
- All calls use `temperature=0.0`
- Uses OpenAI Python SDK (`openai` package)

### How Agents Are Called
All agents use `src/agent_utils.py::call_json_with_validation()`:
- Takes: LLMClient, system_prompt, user_json, Pydantic model class, schema text, optional extra_validator
- Returns: validated dict
- On validation failure: retries up to 2 times using a JSON repair prompt

### Current Hardcoded Values
- **3 experts** in `main_taxonomist.py` line 99: `expert_ids = ["A", "B", "C"]`
- **5 taggers** in `main_taggers.py` line 80: `tagger_ids = ["T1", "T2", "T3", "T4", "T5"]`
- **Voting thresholds** in `main_judge.py` function `compute_skill_level_votes()`:
  - `count >= 4` → auto_include (line 75)
  - `count <= 1` → auto_exclude (line 77)
  - else (2 or 3) → disputed (line 79)
- **LLM model** from `.env` OPENAI_MODEL, same model used for ALL agents

### Current Experiment Infrastructure
- `run_experiments.py` supports `--runs N --prompt_version v2` → outputs to `outputs_exp/v2/run1..runN/`
- `analyze_stability.py` computes: K consistency, element-wise agreement, item perfect agreement, pairwise Cohen's κ, Fleiss' κ
- `Analysis.R` fits G-DINA model with three Q-matrices and computes AIC, BIC, RMSEA, SRMSR

---

## IMPLEMENTATION PLAN — ORDERED BY PRIORITY

### PHASE 0: Automated Evaluation Function (DO THIS FIRST)

**Goal:** Create a single script that takes a Q-matrix CSV path and returns quality metrics as JSON. This is the foundation for all experiments.

**Create file: `evaluate_qmatrix.R`**

This R script should:
1. Accept command-line arguments: `--qmatrix <path>` `--data <dataset_name>` `--output <json_path>`
2. Load the appropriate response data based on `--data`:
   - `"tatsuoka"` → `GDINA::realdata_Tatsuoka1990$dat` (built-in dataset)
   - Future datasets will be file paths
3. Load the Q-matrix from CSV (first column is item_id, remaining columns are skills, values are 0/1)
   - Handle the `*` markers from auditor output: strip non-numeric chars, convert to integer
4. Fit G-DINA model: `result <- GDINA::GDINA(data, Q)`
5. Compute model fit: `mf <- GDINA::modelfit(result)`
6. Extract and compute:
   - `AIC`, `BIC`, `CAIC`, `SABIC` from `result` (use `AIC(result)`, `BIC(result)`, or extract from summary)
   - `RMSEA2`, `SRMSR` from `mf` (may be `NA` if M2 can't be computed — handle gracefully)
   - `n_items`, `n_skills` (dimensions of Q)
   - `n_params` (number of estimated parameters)
   - `log_likelihood` from the model
7. Write JSON output to `--output` path:
```json
{
  "qmatrix_path": "...",
  "dataset": "tatsuoka",
  "n_items": 20,
  "n_skills": 4,
  "AIC": 8843.12,
  "BIC": 9430.04,
  "CAIC": 9567.04,
  "SABIC": 8995.16,
  "RMSEA2": 0.0369,
  "SRMSR": 0.0403,
  "log_likelihood": -4200.56,
  "n_params": 127,
  "converged": true,
  "error": null
}
```
8. If fitting fails (e.g., non-complete Q-matrix), write `"error": "<message>"` and set metrics to `null`.

**Also create: `evaluate_qmatrix.py`** — a Python wrapper that:
1. Calls the R script via `subprocess`
2. Reads the JSON output
3. Returns a Python dict
4. Has a function signature: `evaluate(qmatrix_csv: str, dataset: str = "tatsuoka") -> dict`
5. Also supports batch evaluation: `evaluate_batch(csv_paths: list[str], dataset: str) -> list[dict]`

**Dependency:** Requires R with `GDINA` package installed. Add a check that prints a clear error if R or GDINA is not available.

---

### PHASE 1: Parameterize the Pipeline

**Goal:** Make all hardcoded design choices configurable via CLI flags, without changing defaults.

#### 1A: Add `--model` flag to pipeline.py

**Modify `pipeline.py`:**
- Add `--model` argument (default: `None`, meaning use `.env` value)
- When set, pass it as an environment variable override to each subprocess call:
  ```python
  env = os.environ.copy()
  if args.model:
      env["OPENAI_MODEL"] = args.model
  subprocess.check_call(cmd, env=env)
  ```
- This requires changing the `run()` function to accept an `env` parameter

**Modify `run_experiments.py`:**
- Add `--model` argument, propagated to `pipeline.py`

#### 1B: Add `--n_experts` and `--n_taggers` flags

**Modify `pipeline.py`:**
- Add `--n_experts` (default: 3) and `--n_taggers` (default: 5)
- Pass these to `main_taxonomist.py` and `main_taggers.py` respectively

**Modify `main_taxonomist.py`:**
- Add `--n_experts` argument (default: 3)
- Generate expert IDs dynamically: `expert_ids = [chr(65+i) for i in range(args.n_experts)]` → ["A", "B", "C", ...] 
- The SupervisorAlign currently expects exactly 3 codebooks (codebook_a, codebook_b, codebook_c). This needs to be generalized:
  - Change `SupervisorAlign.align()` to accept `codebooks: dict[str, JsonDict]` instead of three separate arguments
  - Update the validation to check all expert keys dynamically
  - Update the prompt to list codebooks by expert ID
  - Update `supervisor_align.txt` prompt to reference experts generically (not "Expert A, B, C")
- **Be careful:** The SupervisorAlign Pydantic schema (`schemas/supervisor_align_output.py`) has fields `expert_a_skill_ids`, `expert_b_skill_ids`, `expert_c_skill_ids`. These need to be generalized to a dict or list structure. This is a significant schema change — make sure the prompt and validation are updated together.

**Modify `main_taggers.py`:**
- Add `--n_taggers` argument (default: 5)
- Generate tagger IDs dynamically: `tagger_ids = [f"T{i+1}" for i in range(args.n_taggers)]`
- Pass `max_workers=args.n_taggers` to ThreadPoolExecutor

**Modify `main_judge.py`:**
- The judge currently reads exactly T1..T5. Change to discover tagger files dynamically from the votes directory:
  ```python
  vote_files = sorted(Path(args.votes_dir).glob("T*.jsonl"))
  ```
- Remove the hardcoded `v1 = load_votes(...)` through `v5 = load_votes(...)` pattern

#### 1C: Add configurable voting thresholds

**Modify `main_judge.py`:**
- Add `--include_threshold` (default: 4) and `--exclude_threshold` (default: 1) CLI arguments
- In `compute_skill_level_votes()`, replace hardcoded `4` and `1` with parameters
- Pass `n_taggers` through so thresholds can be interpreted relative to committee size
- **Also add**: `--consensus_mode` argument with options:
  - `"threshold"` (current behavior — default)
  - `"majority"` — simple majority: include if > n_taggers/2 agree
  - `"confidence_weighted"` — each tagger's confidence scores are summed; include if weighted sum > threshold (requires tagger output to include confidence — see Phase 3)
  - `"unanimity"` — require all taggers to agree

**Modify `pipeline.py`:**
- Add `--include_threshold`, `--exclude_threshold`, `--consensus_mode` flags
- Pass them through to `main_judge.py`

**Modify `run_experiments.py`:**
- Add the same flags, propagated to `pipeline.py`

#### 1D: Add `--skip_stages` flag

**Modify `pipeline.py`:**
- Add `--skip_stages` argument (comma-separated list, e.g., `"verifier,auditor"`)
- Valid stage names: `solver`, `verifier`, `codebook`, `tag`, `judge`, `aggregate`, `export`, `audit`
- When a stage is skipped:
  - `verifier` skipped → copy `step1_solver_item_dossiers.jsonl` to `step2_verifier_verified_item_dossiers.jsonl` (downstream expects step2 file)
  - `auditor` skipped → just don't run step 8
  - `aggregate` skipped → only export the K_max Q-matrix
  - Other stages cannot be meaningfully skipped (solver, codebook, tag, judge are essential)
- Print a warning for each skipped stage

---

### PHASE 2: Simple Baselines

**Goal:** Create zero-shot and chain-of-thought single-LLM baselines for Q-matrix construction, so we can show the multi-agent pipeline adds value over a single LLM call.

**Create file: `baselines/zero_shot.py`**

This script should:
1. Accept `--input` (items JSONL), `--output` (Q-matrix CSV), `--model` (LLM model name)
2. Load all items
3. Send a single LLM call with ALL items at once, asking it to:
   - Identify the cognitive skills needed across all items (K=3-8)
   - Assign skills to each item
   - Output a Q-matrix directly as JSON
4. Parse the output into a Q-matrix CSV with the same format as TRACE-Q output (item_id, S01, S02, ..., S0K)
5. Use `src/llm_client.py` for the LLM call

**Prompt for zero-shot baseline:**
```
You are a psychometrics expert. Given a set of test items, identify the cognitive skills (3-8 skills) required across all items, then construct a Q-matrix mapping each item to its required skills.

Output JSON:
{
  "skills": [{"skill_id": "S01", "name": "...", "definition": "..."}],
  "q_matrix": [{"item_id": "FS01", "skills": ["S01", "S03"]}, ...]
}
```

**Create file: `baselines/chain_of_thought.py`**

Same as zero-shot but with a two-step prompt:
1. First call: "Solve each item step by step, then identify what cognitive skills are needed."
2. Second call: "Given these solutions and skill analysis, construct the Q-matrix."

This isolates the value of the multi-agent committee from the value of step-by-step reasoning.

**Create file: `baselines/single_expert.py`**

Uses one Expert agent + one Tagger (no committee, no voting) to construct a Q-matrix. This isolates the value of the committee mechanism specifically.

Each baseline outputs a standard Q-matrix CSV that can be fed directly to `evaluate_qmatrix.R`.

---

### PHASE 3: Consensus Mechanism Variants

**Goal:** Implement alternative consensus mechanisms that can be selected via `--consensus_mode`.

The current tagger output already includes `reasoning` for each skill. We need to add **confidence scores** to enable confidence-weighted voting.

#### 3A: Add confidence to tagger output

**Modify `src/tagger.py`:**
- Update `TAGGER_SCHEMA_TEXT` to request a `confidence` field (0.0-1.0) for each tagged skill
- The schema already exists in `schemas/tagger_vote.py` — check if `confidence` is already there; if not, add it

**Modify `prompts/v2/tagger.txt`:**
- Add instruction: "For each skill you tag, provide a confidence score between 0.0 and 1.0 indicating how certain you are that this skill is required."

#### 3B: Implement consensus modes in main_judge.py

**Add to `main_judge.py`:**

```python
def compute_majority_votes(votes_by_tagger, n_taggers):
    """Simple majority: include if > n_taggers/2 agree."""
    skill_counts = {}
    for _tid, vote in votes_by_tagger.items():
        for sid in skill_set(vote):
            skill_counts[sid] = skill_counts.get(sid, 0) + 1
    threshold = n_taggers / 2
    auto_include = [s for s, c in skill_counts.items() if c > threshold]
    auto_exclude = [s for s, c in skill_counts.items() if c <= threshold]
    return {
        "skill_counts": skill_counts,
        "auto_include": sorted(auto_include),
        "auto_exclude": sorted(auto_exclude),
        "disputed": [],
        "has_disputed": False,
        "n_taggers": n_taggers,
    }

def compute_unanimity_votes(votes_by_tagger, n_taggers):
    """Unanimity: include only if ALL taggers agree."""
    skill_counts = {}
    for _tid, vote in votes_by_tagger.items():
        for sid in skill_set(vote):
            skill_counts[sid] = skill_counts.get(sid, 0) + 1
    auto_include = [s for s, c in skill_counts.items() if c == n_taggers]
    auto_exclude = [s for s, c in skill_counts.items() if c < n_taggers]
    return {
        "skill_counts": skill_counts,
        "auto_include": sorted(auto_include),
        "auto_exclude": sorted(auto_exclude),
        "disputed": [],
        "has_disputed": False,
        "n_taggers": n_taggers,
    }

def compute_confidence_weighted_votes(votes_by_tagger, n_taggers, threshold=0.5):
    """Confidence-weighted: sum confidence scores, include if weighted avg > threshold."""
    skill_scores = {}  # skill_id -> list of confidence scores
    for _tid, vote in votes_by_tagger.items():
        for s in vote.get("skills", []):
            sid = str(s.get("skill_id", "")).strip()
            conf = float(s.get("confidence", 1.0))
            skill_scores.setdefault(sid, []).append(conf)
    
    skill_counts = {s: len(scores) for s, scores in skill_scores.items()}
    weighted_avg = {s: sum(scores) / n_taggers for s, scores in skill_scores.items()}
    
    auto_include = [s for s, w in weighted_avg.items() if w > threshold]
    auto_exclude = [s for s, w in weighted_avg.items() if w <= threshold]
    return {
        "skill_counts": skill_counts,
        "weighted_scores": weighted_avg,
        "auto_include": sorted(auto_include),
        "auto_exclude": sorted(auto_exclude),
        "disputed": [],
        "has_disputed": False,
        "n_taggers": n_taggers,
    }
```

Then in the main loop, dispatch based on `--consensus_mode`:
```python
if args.consensus_mode == "threshold":
    vote_stats = compute_skill_level_votes(votes_bundle)  # existing
elif args.consensus_mode == "majority":
    vote_stats = compute_majority_votes(votes_bundle, n_taggers)
elif args.consensus_mode == "unanimity":
    vote_stats = compute_unanimity_votes(votes_bundle, n_taggers)
elif args.consensus_mode == "confidence_weighted":
    vote_stats = compute_confidence_weighted_votes(votes_bundle, n_taggers)
```

#### 3C: (Optional, lower priority) Implement one-round debate

**Create `src/debate.py`:**
- After initial tagging (Step 4), share all 5 taggers' votes with each tagger
- Each tagger gets a second prompt: "Here are the other taggers' votes and reasoning. Revise your vote if needed."
- Run a second round of tagging
- Then apply voting on the revised votes

This would be activated via `--consensus_mode debate` and would add a Step 4b between tagging and judging.

---

### PHASE 4: Multi-Provider LLM Support

**Goal:** Allow using different LLM providers (OpenAI, Anthropic, DeepSeek) and different models per stage.

#### 4A: Extend LLMClient for multiple providers

**Modify `src/llm_client.py`:**

Add provider detection based on model name:
```python
@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    model: str
    seed: Optional[int] = None
    provider: str = "openai"  # "openai", "anthropic", "deepseek"
    base_url: Optional[str] = None  # For OpenAI-compatible APIs

class LLMClient:
    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        load_dotenv(override=False)
        if config is None:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            model = os.getenv("OPENAI_MODEL", "").strip()
            seed_str = os.getenv("OPENAI_SEED", "").strip()
            provider = os.getenv("LLM_PROVIDER", "openai").strip()
            base_url = os.getenv("LLM_BASE_URL", "").strip() or None
            if not api_key:
                raise RuntimeError("Missing OPENAI_API_KEY in environment/.env")
            if not model:
                raise RuntimeError("Missing OPENAI_MODEL in environment/.env")
            seed = int(seed_str) if seed_str else None
            config = LLMConfig(api_key=api_key, model=model, seed=seed, provider=provider, base_url=base_url)
        
        self.config = config
        if config.provider == "anthropic":
            # Use anthropic SDK
            from anthropic import Anthropic
            self._anthropic_client = Anthropic(api_key=config.api_key)
        else:
            # OpenAI or OpenAI-compatible (DeepSeek, etc.)
            kwargs = {"api_key": config.api_key}
            if config.base_url:
                kwargs["base_url"] = config.base_url
            self._client = OpenAI(**kwargs)
```

For Anthropic, the `chat_completions()` method needs a separate code path because Anthropic's API uses `system` as a separate parameter, not in the messages array. Also, Anthropic doesn't support `response_format={"type": "json_object"}` — you need to instruct JSON output in the prompt instead.

For DeepSeek: Use the OpenAI SDK with `base_url="https://api.deepseek.com"`. DeepSeek's API is OpenAI-compatible.

**Key environment variables to support:**
```
# OpenAI (default)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
LLM_PROVIDER=openai

# Anthropic
OPENAI_API_KEY=sk-ant-...   # or ANTHROPIC_API_KEY
OPENAI_MODEL=claude-sonnet-4-20250514
LLM_PROVIDER=anthropic

# DeepSeek
OPENAI_API_KEY=sk-...
OPENAI_MODEL=deepseek-chat
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.deepseek.com
```

#### 4B: Per-stage model assignment

**Create file: `config/experiment_config.yaml`** (example):
```yaml
# Default model for all stages
default_model: gpt-4o-mini
default_provider: openai

# Per-stage overrides (optional)
stages:
  solver:
    model: gpt-4o-mini
  expert:
    model: gpt-4o
  tagger:
    model: gpt-4o-mini
  judge:
    model: gpt-4o
```

**Modify `pipeline.py`:**
- Add `--config` argument that loads a YAML config
- When a per-stage model is specified, set the `OPENAI_MODEL` (and `LLM_PROVIDER`, `LLM_BASE_URL`) environment variables before calling that stage's subprocess

This is lower priority — start with the single `--model` flag that applies to all stages.

---

### PHASE 5: Experiment Runner for Ablation Studies

**Goal:** Create a script that systematically runs different configurations and collects results.

**Create file: `run_ablation.py`**

This script should:
1. Define a list of experiment configurations (or read from a YAML file)
2. For each configuration:
   a. Run the pipeline with appropriate flags
   b. Evaluate the resulting Q-matrix using `evaluate_qmatrix.py`
   c. Store results in a structured JSON file
3. Output a summary comparison table

**Example configuration file: `experiments/ablation_config.yaml`:**
```yaml
dataset: tatsuoka
input: data/items.jsonl
base_output_dir: outputs_ablation
n_runs_per_config: 3  # Run each config 3 times for stability

experiments:
  # --- Consensus mechanism comparison ---
  - name: threshold_4_1
    consensus_mode: threshold
    include_threshold: 4
    exclude_threshold: 1
    
  - name: majority
    consensus_mode: majority
    
  - name: unanimity
    consensus_mode: unanimity
    
  - name: confidence_weighted
    consensus_mode: confidence_weighted

  # --- Committee size comparison ---
  - name: experts_1_taggers_3
    n_experts: 1
    n_taggers: 3
    
  - name: experts_3_taggers_5
    n_experts: 3
    n_taggers: 5
    
  - name: experts_5_taggers_7
    n_experts: 5
    n_taggers: 7

  # --- Stage removal ---
  - name: no_verifier
    skip_stages: verifier
    
  - name: no_auditor
    skip_stages: auditor
    
  - name: no_verifier_no_auditor
    skip_stages: verifier,auditor

  # --- Backbone model comparison ---
  - name: gpt4o_mini
    model: gpt-4o-mini
    
  - name: gpt4o
    model: gpt-4o
```

**Output structure:**
```
outputs_ablation/
  threshold_4_1/
    run1/ ... run3/
  majority/
    run1/ ... run3/
  ...
  results_summary.json    ← Aggregated results across all experiments
  results_summary.csv     ← Same data in tabular format for easy viewing
```

**Create file: `analyze_ablation.py`**

Reads all experiment results, computes:
- Mean and SD of fit indices across runs for each configuration
- Ranking of configurations by each metric
- Best configuration identification
- Prints a formatted comparison table

---

### PHASE 6: Enhanced Stability Analysis

**Modify `analyze_stability.py` to add:**

1. **Unique Q-matrix count**: How many distinct Q-matrices appear across N runs?
2. **Modal Q-matrix**: The most frequent Q-matrix and its frequency (e.g., "Q-matrix X appeared in 34/100 runs")
3. **Probabilistic Q-matrix**: For each cell (item × skill), the proportion of runs where it equals 1. Output as a CSV where values are 0.00-1.00 instead of 0/1.
4. **Fit distribution** (requires R evaluation): For each unique Q-matrix (or a sample if >20 unique), compute G-DINA fit. Report mean, SD, min, max of AIC/BIC across the unique Q-matrices.

Add CLI flags:
- `--n_runs` to specify expected number of runs (for percentage calculations)
- `--evaluate_fit` flag that triggers R-based evaluation (default: off, since it requires R)
- `--output_json` path for structured output (in addition to console printing)

---

### PHASE 7: New Datasets for Generalizability

**Create new input files in `data/` directory:**

Each dataset needs:
1. `data/<name>/items.jsonl` — same format as current items (item_id, stem_text, answer_rules)
2. `data/<name>/expert_q.csv` — expert Q-matrix for comparison (if available)
3. `data/<name>/responses.csv` — response data for G-DINA fitting (if available)
4. `data/<name>/README.md` — description of the dataset, source, number of items, known K

**Priority datasets to prepare:**
1. **ECPE** (Examination for the Certificate of Proficiency in English) — K=3, available in CDM R packages. Items are reading/grammar. Need to extract item stems or descriptions.
2. **TIMSS-related items** — if publicly available CDM analyses exist with item text.
3. **Science assessment items** — look for published CDM studies with item text available.

For each new dataset, also update `evaluate_qmatrix.R` to load the appropriate response data.

---

## IMPLEMENTATION NOTES

### Testing Strategy
After each phase, verify:
1. `python pipeline.py all` still works with no arguments (backward compatibility)
2. New flags work: `python pipeline.py --model gpt-4o --n_taggers 3 --consensus_mode majority all`
3. `run_experiments.py` propagates new flags correctly
4. Output file formats haven't changed

### Error Handling
- If R is not available, `evaluate_qmatrix.py` should print a clear error and exit gracefully
- If an LLM provider is not available (e.g., no Anthropic key), the pipeline should fail at startup with a clear message
- If `--n_experts 1` is used, the Supervisor stages should be skipped automatically (no alignment needed for a single expert)
- If `--n_taggers` < 3, warn that voting thresholds may not be meaningful

### Cost Awareness
- Add a `--dry_run` flag to `pipeline.py` that prints what would be executed without making LLM calls
- Add a `--estimate_cost` flag that estimates API cost based on number of items × number of agents × approximate tokens per call
- Log total tokens used and cost after each run (OpenAI API returns usage in response)

### Logging
- Add a `run_log.json` to each run's output directory containing:
  - All CLI flags used
  - Model name and provider
  - Start/end timestamps
  - Total API calls made
  - Total tokens used (input + output)
  - Any errors encountered

---

## PRIORITY ORDER

If you have limited time, implement in this exact order:

1. **Phase 0** — `evaluate_qmatrix.R` and `evaluate_qmatrix.py` (everything depends on this)
2. **Phase 1C** — Configurable voting thresholds and `--consensus_mode` (smallest code change, immediate experiment value)
3. **Phase 1A** — `--model` flag (enables backbone model comparison)
4. **Phase 2** — Zero-shot and single-expert baselines (essential for the paper)
5. **Phase 1B** — `--n_experts` and `--n_taggers` (committee size experiments)
6. **Phase 1D** — `--skip_stages` (stage removal ablation)
7. **Phase 5** — `run_ablation.py` (automates the full experiment sweep)
8. **Phase 3** — Consensus mechanism variants (confidence-weighted, debate)
9. **Phase 4** — Multi-provider LLM support
10. **Phase 6** — Enhanced stability analysis
11. **Phase 7** — New datasets
