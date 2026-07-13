# TRACE-Q Evaluation Framework

**Status:** v1.1 FROZEN (2026-07-13) — metric set unchanged from v1.0 (calibrated against the V1 sensitivity study). Changes require an explicit version bump; metric changes additionally require re-running V1.

**v1.0 → v1.1 changes** (design amendments made before the definitive comparison matrix ran; metric set untouched):
1. **Single K condition.** The fixed-K generation condition is removed: K=4 had no principled justification for constraining *generation* (it derived from TSQE's best-fit K, which justifies TSQE's choice only, and it was the worst-scoring candidate in our own structure-discovery evaluation). All methods now run under one symmetric condition: **auto — model/pipeline selects K within 3–8** (band justified by identifiability: 20 items, 2^K latent classes; and by symmetry — the pipeline's internal constraint is 3–8). Same-K fit comparisons (SRMSR/AIC/BIC) become *conditional analyses* on modal-K subsets rather than a designed condition; K-instability and within-modal-K ontology instability are decomposed by stability layers 1 and 3 from the same runs. Completed fixed_4 runs are archived as supplementary material in `baseline_evaluation/supplementary_fixed_k4/`.
2. **B3 uses N=5 samples** (odd → cell votes never tie, removing the tie-break convention; standard self-consistency range). Measured budget asymmetry recorded: N=5 ≈ 10% of our methods' per-run tokens (346,551 vs ~34,000 on GPT-5.5) — the asymmetry favors the baseline claim either way and is reported, not hidden.
3. **TSQE reference K is selected by BIC sweep over 3–8** (the data-driven analogue of auto). On Tatsuoka it selects K=4 (BIC: K3 9180.1, K4 9177.0, K5 9225.5, K6 9365.4, K7 9783.1, K8 11657.5), retroactively grounding the legacy K=4 convention.
4. Temperature/seed policy: temperature 0 where supported; models that reject non-default temperature (GPT-5.x reasoning family) run at model default with the fallback recorded per run (`temperature_fallbacks` in config.json). OpenAI runs use distinct recorded per-run seeds; other providers record `seed: null`.

---

## 1. Purpose and Principles

This document defines the evaluation system, baselines, and experimental design for TRACE-Q **before** the construction method is finalized (evaluation-first development).

Core principles:

1. **Method-agnostic.** The evaluation side never inspects how a Q-matrix was produced. Any method — any version of our methods, a single-shot LLM, a data-driven algorithm, or a published expert Q — is evaluated identically through a common output contract (Section 3).
2. **Frozen before comparison.** Metrics, conditions, and run counts are fixed in this document before formal method comparisons begin, to prevent metric shopping.
3. **Quality and stability are reported jointly.** Either one alone is gameable: a pipeline that always outputs the same wrong Q is perfectly stable; a pipeline with good average fit but high variance is unusable. The headline figure of the project is a 2-D plot: stability (x) × quality (y), one point per method with error bars.

## 2. Claims Under Test

- **C1 (evaluation contribution).** Q-matrix quality can be evaluated through a validated, multi-dimensional framework combining generation stability and generation quality.
- **C2 (method contribution).** Single-shot LLM generation < our methods; our methods approach or exceed the published expert Q-matrix — where "exceed" is adjudicated by response data (the expert Q is treated as a competing hypothesis, not ground truth).

## 3. Run Output Contract

Every method produces one directory per run:

```
<run_id>/
  Q.csv           # items x skills binary matrix, header = skill ids
  codebook.json   # optional: skill names, definitions, criteria (LLM methods)
  config.json     # method name/version, model, seed, K condition,
                  # dataset id, token cost, timestamp
```

The evaluation harness consumes only directories conforming to this contract. Future changes to our methods require no changes on the evaluation side.

## 4. Evaluation Dimensions and Core Metrics

One primary metric per dimension (kept deliberately lean). Validity ranges
follow the V1 sensitivity study (Section 5a):

| # | Dimension | Primary metric | Needs response data | Valid K range | Tool |
|---|-----------|----------------|---------------------|---------------|------|
| A | Structural validity | Completeness / identifiability checklist (violations count) | No | all K | custom Python |
| B | Empirical fit | SRMSR (RMSEA2 secondary; AIC/BIC/CAIC/SABIC as reference columns) | Yes | K ≤ 5 (20-item test) | GDINA |
| C | Data adjudication | Aligned agreement with the TSQE-estimated Q at the method's K (NPCDTools::TSQE, GDI ref method) | Yes | all K | NPCDTools + custom |
| D | Convergent validity | Aligned agreement with expert Q (column matching; report precision/recall of 1-cells) | No | all K | custom |
| E | Diagnostic utility | ARI between student partitions (full sample, no posterior filtering) | Yes | all K | mclust |

**Two comparison tracks** (a consequence of the V1 findings; v1.1 makes the
same-K track conditional rather than designed):

- **Same-K track** (conditional analysis on modal-K subsets — runs of two
  methods that happen to share the same K): primary ranking metric = SRMSR,
  with AIC/BIC as reference. Valid because information criteria and absolute
  fit are corruption-sensitive when K is small relative to test length.
- **Cross-K track** (the default: methods select K within 3–8): information
  criteria and RMSEA2/SRMSR are NOT comparable across K. Primary ranking
  metrics = TSQE agreement (C) and classification ARI (E), both K-agnostic.

**Circularity rules:** metric C is 1.0 by construction for the TSQE baseline and
must not rank it; metric D likewise for the expert Q. Each reference-based
metric excludes its own reference from ranking.

Classification accuracy (GDINA::CA) was REMOVED from the framework: the V1
study showed it is insensitive to Q corruption and can even increase with
corruption (it measures the model's classification confidence under its own
assumptions, not Q correctness).

**Stability** (reliability of the construction procedure), measured at four layers across repeated runs:

| Layer | Metric |
|-------|--------|
| K | Distribution of selected K across runs |
| Codebook | Semantic skill matching across runs (embedding + Hungarian alignment) |
| Matrix | Aligned Fleiss' kappa; element-wise agreement; item-level perfect agreement |
| Classification | Between-run ARI on student diagnoses (full sample) |

Interpretation rules for E/classification-layer ARI (read together with A and C):

- **Hierarchical coarsening** (each group of ours is a union of expert groups): benign granularity difference.
- **Cross-cutting partitions** (low ARI despite clean structural checks): skill boundaries misaligned with real cognitive differences — the harmful failure mode.
- **Spurious distinction** (a skill the data cannot measure): surfaces as duplicate/near-duplicate columns or missing single-attribute items in the structural checklist (A), and as depressed TSQE agreement (C).

## 5. Framework Validation (prerequisite experiments)

The framework itself is validated before it is used to compare methods:

- **V1 Metric sensitivity simulation.** Density-preserving corruption of a
  reference Q (equal 1→0 and 0→1 flips) at 5% / 10% / 20%; verify each quality
  metric degrades monotonically. Unbalanced random flips are invalid: they raise
  Q density, which improves saturated G-DINA fit and confounds the study.
- **V2 Contamination probe.** For each dataset, ask each target LLM to reproduce the published expert Q verbatim. Results archived; if reproduction succeeds, the perturbed item set (Section 7) is promoted from defense to primary experiment.

### 5a. V1 findings on Tatsuoka (2026-07-10/11, basis for the frozen metric table)

- AIC/BIC/CAIC/SABIC: perfectly monotone at K=4; INVERTED at K=8 (20 items vs
  2^8 latent classes = over-parameterized regime) → K ≤ 5 validity bound.
- RMSEA2/SRMSR: near-monotone at K=4 (plateau at 20% corruption); RMSEA2 is
  incomputable at K=8 (M2 statistic undefined).
- CA (tau): insensitive at K=4 and inverted at K=8 → removed from framework.
- Expert agreement: monotone by construction (corruption is defined relative to
  it) — V1 does not independently validate dimension D.
- Raw archives: eval_out/v1 (balanced), eval_out/v1_unbalanced, eval_out/v1_k4.

## 6. Baselines

| Baseline | Description | Purpose |
|----------|-------------|---------|
| B1 | Naive single-prompt Q generation | Floor |
| B2 | Strong CoT single-prompt (same task information as our methods) | Rules out "bad prompt" explanation |
| B3 | Self-consistency (N=5 samples of B2 at temp 0.7 + modal-K filter + aligned majority vote) | The real competitor: structure vs unstructured ensembling (≈10% of our methods' token budget — asymmetry favors the claim either way) |
| TSQE | Data-driven Q estimation from response data, K = BIC-optimal over 3–8 | Non-LLM reference |
| Expert Q | Published expert Q-matrix (single instance, constant reference line) | Convergent target and competing hypothesis |

## 7. Datasets

| Dataset | Role | Requirements met |
|---------|------|------------------|
| Fraction subtraction (Tatsuoka, 20 items) | Primary battleground | Response data + published expert Q + item text |
| Structure-preserving perturbed fraction set | Contamination control: numbers replaced under structural constraints (same like/unlike denominators, borrowing, mixed-number pattern); expert Q rows transfer to perturbed items; metric = invariance of the generated Q mapped back to originals | Constraint checker script required |
| Additional dataset(s), other domain/language | Generalizability | See criteria below |

Selection criteria for additional datasets, in priority order:

1. **Item text available** (the binding constraint — many public CDM datasets release responses and Q but not stems; our methods require stems);
2. Public response data (without it, dimensions B/C/E are unavailable);
3. Published expert Q (ideal);
4. Different domain or language;
5. Moderate size (15–40 items).

Every newly added dataset first passes the contamination probe (V2).

## 8. Experimental Design (v1.1)

- **K condition:** single symmetric condition — every method selects K within 3–8 (see v1.1 change 1). Same-K fit comparisons are conditional analyses on modal-K subsets.
- **Model panel (pinned):** anchor `gpt-5.5-2026-04-23` (direct OpenAI, full B1/B2/B3 + our methods); `anthropic/claude-sonnet-5`, `google/gemini-3.5-flash`, `deepseek/deepseek-v4-pro` via OpenRouter (B2/B3 + our methods). V2 contamination probe runs per model (GPT-5.5: aligned 0.725).
- **Runs:** ≥10 independent runs per method × model × dataset (expert Q and TSQE enter as single deterministic references).
- **Statistics:** Mann-Whitney U for between-method comparisons on run-level metrics; bootstrap CIs; distributions reported, not single points.
- **Cost reporting:** token cost per run reported for all LLM methods (measured on GPT-5.5: our methods ≈ 346.6k tokens/run over 165 calls; B2 ≈ 6.8k; B3 = 5 × B2).
- **Results locations:** active runs in `baseline_evaluation/runs/` (contract dirs, git-tracked primary data); reports in `baseline_evaluation/report/`; fixed_4-era supplementary archive in `baseline_evaluation/supplementary_fixed_k4/`.

## 9. Phased Plan

| Phase | Content | Depends on |
|-------|---------|-----------|
| 0 | Freeze run contract + this spec | — |
| 1 | Evaluation infrastructure: R evaluator (fit, persisted), TSQE reference, structural checker, 4-layer stability evaluator, unified report generator, V1, V2 | 0 |
| 2 | Baselines B1/B2/B3, TSQE, expert-Q packaging | 0 |
| 3 | Perturbed item set; additional dataset onboarding | 0, V2 |
| 4 | Our methods: conform to contract, formal runs, iterate (each method version only re-runs the harness) | 1–3 |
| 5 | Full comparison matrix, headline stability × quality figure, statistics | 4 |

Critical path: V1 and V2 complete before any formal method runs (Phase 4).
