# Agent-Qmatrix (Multi-agent Q-matrix pipeline)

End-to-end multi-agent pipeline: Solver → Verifier → **Expert Committee + Supervisor** → 5×Tagger → Judge → Export → **Auditor**.

All stages are **LLM-only** (no domain-specific Python rule calculations), all model calls use `temperature=0`, and all outputs are **STRICT JSON** validated with Pydantic. **Each run starts from scratch** with no caching.

## Use Cases

The generated Q-matrix can be used for **Cognitive Diagnostic Models (CDM)**:
- DINA, DINO, GDINA
- Nonparametric CDM
- Other attribute mastery models

## Directory Structure

- `src/`: Python source code
- `prompts/`: Prompt text files
- `schemas/`: Pydantic schemas (output validation)
- `data/`: Input JSONL files
- `outputs/`: Output files

## Installation

```bash
cd /Users/weixuan/Desktop/Agent-Qmatrix
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```bash
cat > .env << 'EOF'
OPENAI_API_KEY=YOUR_KEY_HERE
OPENAI_MODEL=gpt-4o-mini
EOF
```

## Run Full Pipeline (Recommended)

```bash
python pipeline.py all
```

Each run automatically clears old output files and recalculates everything from scratch.

## Prompt Versioning + Multiple Runs (Experiment Management)

To facilitate comparison of different prompt versions (v1/v2) and stability testing through repeated runs, this project supports:
- `--prompts_dir`: Prompt directory (e.g., `prompts/v1`, `prompts/v2`)
- `--outputs_dir`: Output directory (e.g., `outputs2/run1`)

Example: Use `prompts/v1` and write results to `outputs2`:

```bash
python pipeline.py --prompts_dir prompts/v1 --outputs_dir outputs2 all
```

Repeated runs (same prompt version, multiple runs with isolated outputs):

```bash
# Generate complete results in outputs_exp/v1/run1, run2, run3
python run_experiments.py --prompt_version v1 --runs 3
```

You can create `prompts/v2/` to try new prompts, then run:

```bash
python run_experiments.py --prompt_version v2 --runs 3
```

## Stage-by-Stage Execution

### 1) Solver

```bash
python main.py --input data/items.jsonl --out outputs/step1_solver_item_dossiers.jsonl
```

### 2) Verifier (Audit and fix Solver)

```bash
python main_verify.py --input outputs/step1_solver_item_dossiers.jsonl --out outputs/step2_verifier_verified_item_dossiers.jsonl
```

### 3) Expert Committee + Supervisor (Generate skill codebook)

```bash
python main_taxonomist.py --input outputs/step2_verifier_verified_item_dossiers.jsonl --out outputs/step3_taxonomist_skill_codebook_v1.json
```

**New Process**:
1. **3 Experts (domain experts) run in parallel** independently to identify skills
2. **Supervisor (senior expert) consolidates** and outputs a unified final codebook

Output files:
- `step3_expert_codebooks.json`: Independent results from 3 Experts
- `step3_supervisor_output.json`: Supervisor's consolidation process (skill alignment, decision records)
- `step3_taxonomist_skill_codebook_v1.json`: Final skill codebook

### 4) Tagger Committee (T1..T5 five independent taggers with reasoning)

```bash
# Parallel execution (default, faster)
python main_taggers.py --parallel --dossiers outputs/step2_verifier_verified_item_dossiers.jsonl --codebook outputs/step3_taxonomist_skill_codebook_v1.json --out_dir outputs/step4_tagger_votes

# Sequential execution (for debugging)
python main_taggers.py --dossiers outputs/step2_verifier_verified_item_dossiers.jsonl --codebook outputs/step3_taxonomist_skill_codebook_v1.json --out_dir outputs/step4_tagger_votes
```

Each Tagger provides `reasoning` for the skills they tag, explaining why each skill is necessary.

### 5) Judge (Auto-pass if ≥4/5 agree on same set, otherwise LLM adjudication)

```bash
python main_judge.py --dossiers outputs/step2_verifier_verified_item_dossiers.jsonl --codebook outputs/step3_taxonomist_skill_codebook_v1.json --votes_dir outputs/step4_tagger_votes --out outputs/step5_judge_adjudicated_dossiers.jsonl
```

Judge references each Tagger's `reasoning` to resolve disagreements.

### 6) Export (Export Q-matrix + reliability report)

```bash
python main_export_q.py --dossiers outputs/step5_judge_adjudicated_dossiers.jsonl --codebook outputs/step3_taxonomist_skill_codebook_v1.json --out_csv outputs/step6_export_Q_matrix_v1.csv --out_md outputs/step6_export_reliability_report.md
```

### 7) Auditor (Final review of Q-matrix)

```bash
python main_auditor.py --dossiers outputs/step2_verifier_verified_item_dossiers.jsonl --codebook outputs/step3_taxonomist_skill_codebook_v1.json --q_matrix outputs/step6_export_Q_matrix_v1.csv --reliability outputs/step6_export_reliability_per_item.csv
```

Auditor will:
1. Read current Q-matrix and Tagger voting consistency
2. Independently review skill tagging for each item
3. Flag errors and controversial entries
4. Output a corrected Q-matrix (controversial cells marked with `*`)

## Output File Descriptions

| File | Description |
|------|-------------|
| `step1_solver_item_dossiers.jsonl` | Solver output (solution steps and standard answers for each item) |
| `step2_verifier_verified_item_dossiers.jsonl` | Dossier after Verifier review |
| `step3_expert_codebooks.json` | Independent codebooks from 3 Experts |
| `step3_supervisor_output.json` | Supervisor's consolidation process |
| `step3_taxonomist_skill_codebook_v1.json` | Final skill codebook |
| `step4_tagger_votes/T1..T5.jsonl` | Independent votes from 5 Taggers (with reasoning) |
| `step5_judge_adjudicated_dossiers.jsonl` | Final dossier after Judge adjudication |
| `step6_export_Q_matrix_v1.csv` | Final Q-matrix |
| `step6_export_reliability_per_item.csv` | Tagger consistency details per item |
| `step6_export_reliability_report.md` | Reliability report (includes skill names and definitions) |
| `step7_auditor_review.jsonl` | Auditor review details (per item) |
| `step7_auditor_Q_matrix_reviewed.csv` | Reviewed Q-matrix (with `*` controversy markers) |
| `step7_auditor_summary.md` | Audit summary report |

## Agent Role Descriptions

| Agent | Role | Responsibility |
|-------|------|----------------|
| Solver | Solution expert | Generate solution steps and standard answers |
| Verifier | Reviewer | Independently solve, review and correct Solver |
| **Expert (×3)** | **Domain expert** | **Independently identify skill codebook** |
| **Supervisor** | **Senior expert** | **Consolidate and output unified codebook** |
| Tagger (×5) | Annotator | Independently tag skills + provide reasoning |
| Judge | Adjudicator | Resolve disagreements based on reasoning quality |
| **Auditor** | **Review expert** | **Final review of Q-matrix, flag errors and controversies** |

## Expert Committee Mechanism

To improve the stability of skill codebooks, a **committee mechanism** is used:

1. **3 Experts independently identify skills in parallel**
   - Use the same prompt
   - Unaware of each other's results
   - Output their own skill codebooks

2. **Supervisor consolidates**
   - Identify "substantially identical" skills (even if names differ)
   - Count consensus level (3/3, 2/3, 1/3)
   - Higher consensus skills are more reliable
   - Resolve disagreements and output unified codebook

**Transparent Output**: All intermediate results are saved, allowing traceability of every decision.

## Important Solver Stage Behaviors

- **Format Validation**: Solver output is validated with Pydantic; if JSON is invalid/fields don't match, retry up to 2 times.
- **Format Consistency**: The last step must end with `Final answer: <ANSWER>`, and `<ANSWER>` must exactly match the string in `answer_canonical[0]`.
- **Correctness Verification**: Mathematical correctness of answers is verified by Verifier; Solver is only responsible for format.
