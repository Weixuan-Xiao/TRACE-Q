# Evaluation Harness (Phase 1 of docs/evaluation_framework.md)

Method-agnostic evaluation over contract run directories
(`<run_id>/{Q.csv, codebook.json?, config.json}`).

## Command sequence

```bash
# One-time: export the published expert Q (committed as data/expert_q_tatsuoka.csv)
Rscript eval/export_expert_q.R

# Convert legacy experiment runs to contract format
python -m eval.convert_legacy --experiment prompt_experiment/v5_guided_fixedseed_K4 --k 4 --out eval_runs

# Validate contract run dirs
python -m eval.contract eval_runs

# Single-Q tools
python evaluate_qmatrix.py <Q.csv> tatsuoka          # GDINA fit indices (JSON)
python -m eval.check_structure <Q.csv>               # data-free structural checks
python -m eval.expert_agreement --qmatrix <Q.csv>    # aligned agreement vs expert Q
python -m eval.tsqe --qmatrix <Q.csv>                # aligned agreement vs TSQE Q (same K)
python -m eval.ari --qmatrix_a <Q.csv> --qmatrix_b <Q.csv>   # classification ARI

# Unified report: quality + 4-layer stability per (method, dataset, k_condition) group
python -m eval.report --runs_root eval_runs --out eval_out/r1 --expert_q data/expert_q_tatsuoka.csv
#   outputs: report.json, summary_quality.csv, summary_stability.csv, scatter.csv
#   per-run results cached under eval_out/r1/per_run/ (use --force to recompute)
#   flags: --skip-embeddings (no codebook layer), --skip-ari (no classification layer)

# V1: metric sensitivity (density-preserving corruption of the expert Q; ~31 GDINA fits)
python -m eval.v1_sensitivity --replicates 10 --seed 42 --out eval_out/v1

# V2: contamination probe (asks LLM to reproduce the expert Q; needs OPENAI_API_KEY)
python -m eval.v2_contamination --dataset tatsuoka --models gpt-4o-mini --out eval_out/v2
#   non-OpenAI models: --provider openrouter (needs OPENROUTER_API_KEY)

# Phase 2 baselines (B1 naive / B2 strong-CoT / B3 self-consistency) -> contract run dirs
python -m eval.baselines --baseline b1 --model gpt-5.5-2026-04-23 --provider openai \
    --k_condition fixed_4 --runs 10 --out eval_runs/phase2
#   --provider openrouter for anthropic/claude-sonnet-5, google/gemini-3.5-flash,
#   deepseek/deepseek-v4-pro; B3: --n_samples N (token-matched to our methods)

# Reference runs (expert Q + TSQE Q as contract dirs; circularity: each
# reference-based metric must not rank its own reference)
python -m eval.package_reference --out eval_runs/phase2

# Our methods on a specific model, seed recorded per run:
python run_experiments.py --cmd all --prompt_version v5_guided --runs 10 \
    --base_outputs prompt_experiment/<name> --target_k_exact 4 \
    --model gpt-5.5-2026-04-23 --guides_dir guides --seed_base 100

# Unit tests
python -m pytest tests/ -q
```

Notes: GDINA fits take seconds each and are cached by Q-content hash where
possible. RMSEA2 is unavailable at K=8 on 20 items (M2 statistic incomputable);
SRMSR still reports. `eval_runs/` and `eval_out/` are gitignored (regenerable).
