# Agent-Qmatrix: Technical Method Summary

## 1. Project Goal

Construct a **Q-matrix** (binary items × skills matrix) for **Cognitive Diagnostic Models (CDM)** using a fully LLM-driven multi-agent pipeline. The Q-matrix maps each test item to the cognitive skills required to solve it, enabling diagnostic assessments with models such as DINA, DINO, and GDINA.

## 2. Core Design Principles

| Principle | Implementation |
|-----------|---------------|
| **LLM-only** | All stages use LLM reasoning; no hardcoded domain rules |
| **Deterministic** | All LLM calls use `temperature=0` via OpenAI API (model: `gpt-4o-mini`) |
| **Strict validation** | Every agent output is validated against Pydantic schemas with auto-retry (up to 2 fix attempts) |
| **Committee mechanism** | Multiple independent agents at key stages to reduce single-point-of-failure risk |
| **Full traceability** | All intermediate outputs (expert codebooks, tagger reasoning, judge notes, vote stats) are persisted |
| **From-scratch runs** | Each run clears previous outputs; no caching between runs |

## 3. Pipeline Architecture (8 Steps)

```
Input (items.jsonl)
  │
  ├── Step 1: Solver          → Step-by-step solutions
  ├── Step 2: Verifier         → Independently re-solves & corrects
  ├── Step 3: Codebook         → Expert Committee (×3) + Two-phase Supervisor
  │     ├── 3a: 3 Experts (parallel) → 3 independent codebooks (K=3-8 each)
  │     ├── 3b: Supervisor_Align     → Standardized candidate skill list
  │     └── 3c: Supervisor_Consolidate → Final unified codebook (K=3-8)
  ├── Step 4: Tagger (×5)     → 5 independent taggers annotate each item
  ├── Step 5: Judge            → Skill-level voting + LLM adjudication
  ├── Step 6: Aggregator       → Merge skills to create K-1, K-2 codebooks
  ├── Step 7: Export           → Q-matrix CSVs + reliability report
  └── Step 8: Auditor          → Final quality review per K-level
```

## 4. Agent Roles

### Step 1–2: Solution Generation & Verification
- **Solver**: Generates step-by-step solutions with `Final answer: <ANSWER>` format.
- **Verifier**: Independently re-solves, compares with Solver, corrects errors. Output: verified dossiers (item + solver + verifier).

### Step 3: Skill Codebook Construction (Two-Phase Supervisor)
- **Expert (×3)**: Three domain experts independently identify K=3-8 skills from verified dossiers. Same prompt, parallel execution. Each outputs a full codebook with `skill_id`, `name`, `definition`, `inclusion_criteria`, `exclusion_criteria`, `examples`, `prerequisites`.
- **Supervisor_Align**: Aligns skills across 3 expert codebooks — identifies equivalent skills (even with different names), assigns `canonical_id` (C01, C02...), records consensus level (3/3, 2/3, 1/3). Does NOT make merge/remove decisions.
- **Supervisor_Consolidate**: Takes alignment output + expert codebooks + dossiers. Makes final merge/keep/remove/refine decisions. Outputs unified codebook with S01-S08 IDs (3-8 skills). Higher consensus → stronger inclusion signal.

### Step 4–5: Item Annotation & Adjudication (Skill-Level Voting)
- **Tagger (×5)**: Five independent taggers annotate each item against the codebook. Each provides `skills` list with `skill_id`, `evidence_step_ids`, and `reasoning`.
- **Judge**: Implements **skill-level voting** (not set-level):
  - For each skill: count how many taggers (out of 5) tagged it.
  - **Auto-include** (≥4/5): strong consensus, no LLM call needed.
  - **Auto-exclude** (≤1/5): weak support, excluded.
  - **Disputed** (2/3 out of 5): sent to Judge LLM for evidence-based adjudication.
  - Judge follows Rule A (evidence-first inclusion) and Rule B (explanatory completeness).
  - If no disputed skills → Judge LLM is not called (saves API cost).

### Step 6: Aggregation (Multi-K)
- **Aggregator**: Given the fine-grained codebook (K_max), creates coarser versions by semantically merging related skills.
  - Default: auto-computes target K values as `[K_max-1, K_max-2]` (if K_max > 3).
  - Uses merged IDs (M01, M02...) with OR-logic mapping (if any original skill = 1, merged = 1).
  - Result: up to 3 Q-matrices (K_max, K_max-1, K_max-2).

### Step 7: Export
- Generates Q-matrix CSV per K-level, reliability report (per-item tagger agreement: full_agree, supermajority, avg_jaccard).

### Step 8: Audit
- **Auditor**: Reviews each item's Q-vector per K-level. Independently determines required skills, compares with current annotations. Verdicts: `correct`, `error`, `controversial`. Modified cells marked with `*` in output CSV.

## 5. Data Flow

**Input format** (`data/items.jsonl`):
```json
{"item_id": "FS01", "stem_text": "5/3 - 3/4", "answer_rules": "Return result in lowest terms..."}
```

**Current test domain**: Arithmetic with fractions and mixed numbers (subtraction and simplification), 20 items (FS01–FS20).

**Key intermediate files**:
- `step3_skill_codebook.json`: Final codebook with `skills` array
- `step4_tagger_votes/T1..T5.jsonl`: Independent tagger votes with reasoning
- `step5_judge_adjudicated_dossiers.jsonl`: Adjudicated results with `vote_stats`
- `step6_Q_matrix_K{k}.csv`: Q-matrix per K-level
- `step8_auditor_Q_matrix_K{k}_reviewed.csv`: Audited Q-matrix (cells with `*` = modified)

## 6. Experiment Management

- **Prompt versioning**: `prompts/v1/`, `prompts/v2/` — selected via `--prompts_dir`.
- **Repeated runs**: `run_experiments.py --prompt_version v2 --runs 10 --start_run 1` → outputs to `outputs_exp/v2/run1..run10/`.
- **Stability analysis**: `analyze_stability.py` computes cross-run metrics:
  - K Consistency (whether K_max is stable)
  - Element-wise Agreement Rate
  - Item-level Perfect Agreement
  - Pairwise Cohen's Kappa & Hamming distance
  - Fleiss' Kappa (multi-run inter-rater reliability)
  - Auditor impact comparison (step6 vs step8)

## 7. Empirical Observations (v2, 10 runs, 20 items)

| Metric | step6 (Pre-Audit) | step8 (Post-Audit) |
|--------|---:|---:|
| K Consistency | 9/10 (90%) K=5 | — |
| Element-wise Agreement | 89.3% | 89.7% |
| Item Perfect Agreement | 0% | 0% |
| Fleiss' Kappa | 0.646 | 0.656 |
| Min Cohen's Kappa | 0.177 | 0.181 |

**Key finding**: Despite `temperature=0`, significant cross-run instability remains. No item achieves perfect agreement across 10 runs. The Auditor has negligible impact on stability (~1.8 cells flipped per run). Instability originates primarily from the Expert Committee / Supervisor codebook generation stage.

## 8. Technology Stack

- Python 3.13, OpenAI API (`openai>=1.40,<2.0`)
- Pydantic v2 for schema validation
- `python-dotenv` for env config, `tqdm` for progress
- No external ML/NLP libraries; pure LLM reasoning

## 9. File Structure

```
├── pipeline.py              # Main pipeline runner (8-step orchestrator)
├── run_experiments.py        # Repeated experiment runner
├── analyze_stability.py      # Cross-run stability analysis
├── main.py                   # Step 1: Solver
├── main_verify.py            # Step 2: Verifier
├── main_taxonomist.py        # Step 3: Expert Committee + Supervisor
├── main_taggers.py           # Step 4: Tagger Committee
├── main_judge.py             # Step 5: Judge (skill-level voting)
├── main_aggregator.py        # Step 6: Aggregator
├── main_export_q.py          # Step 7: Export
├── main_auditor.py           # Step 8: Auditor
├── src/                      # Agent implementations
│   ├── llm_client.py         # OpenAI wrapper (temperature=0)
│   ├── expert.py, supervisor.py, judge.py, aggregator.py, auditor.py ...
├── schemas/                  # Pydantic output schemas
├── prompts/v2/               # Prompt files
│   ├── expert.txt, supervisor_align.txt, supervisor_consolidate.txt
│   ├── tagger.txt, judge.txt, aggregator.txt, auditor.txt
├── data/items.jsonl           # Input items
└── outputs_exp/v2/run*/       # Experiment outputs
```
