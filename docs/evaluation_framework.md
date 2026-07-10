# TRACE-Q Evaluation Framework

**Status:** v1 draft — framework frozen at the structural level; metric details may be fine-tuned before pre-registration freeze.

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

One primary metric per dimension (kept deliberately lean):

| # | Dimension | Primary metric | Needs response data | Tool |
|---|-----------|----------------|---------------------|------|
| A | Structural validity | Completeness / identifiability checklist (violations count) | No | custom Python |
| B | Empirical fit | RMSEA2, SRMSR (AIC/BIC/CAIC/SABIC as reference columns) | Yes | GDINA |
| C | Data adjudication | Qval modification-suggestion rate (% of cells the data would revise) | Yes | GDINA::Qval |
| D | Convergent validity | Aligned agreement with expert Q (Hungarian column matching; report precision/recall of 1-cells) | No | custom |
| E | Diagnostic utility | (E1) CA classification accuracy per skill; (E2) ARI between student partitions (full sample, no posterior filtering) | Yes | GDINA::CA, mclust |

**Stability** (reliability of the construction procedure), measured at four layers across repeated runs:

| Layer | Metric |
|-------|--------|
| K | Distribution of selected K across runs |
| Codebook | Semantic skill matching across runs (embedding + Hungarian alignment) |
| Matrix | Aligned Fleiss' kappa; element-wise agreement; item-level perfect agreement |
| Classification | Between-run ARI on student diagnoses (full sample) |

Interpretation rules for E2/classification-layer ARI:

- **Hierarchical coarsening** (each group of ours is a union of expert groups): benign granularity difference.
- **Cross-cutting partitions** (low ARI, normal CA): skill boundaries misaligned with real cognitive differences — the harmful failure mode.
- **Spurious distinction** (CA ≈ 0.5 for a skill): a skill the data cannot measure. E1 and E2 must therefore be read together.

## 5. Framework Validation (prerequisite experiments)

The framework itself is validated before it is used to compare methods:

- **V1 Metric sensitivity simulation.** Flip 5% / 10% / 20% of cells in the expert Q; verify every quality metric degrades monotonically with corruption. Analogous perturbation check for stability metrics.
- **V2 Contamination probe.** For each dataset, ask each target LLM to reproduce the published expert Q verbatim. Results archived; if reproduction succeeds, the perturbed item set (Section 7) is promoted from defense to primary experiment.

## 6. Baselines

| Baseline | Description | Purpose |
|----------|-------------|---------|
| B1 | Naive single-prompt Q generation | Floor |
| B2 | Strong CoT single-prompt (same task information as our methods) | Rules out "bad prompt" explanation |
| B3 | Self-consistency (N samples + vote), **token-budget matched** to our methods | The real competitor: structure vs unstructured ensembling |
| TSQE | Data-driven Q estimation from response data | Non-LLM reference |
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

## 8. Experimental Design

- **K conditions:** pipeline-selected K, and fixed-K condition(s) matching the expert Q / literature convention. Both pre-declared.
- **Runs:** ≥10 independent runs per method × condition × dataset (expert Q enters as a single constant).
- **Statistics:** Mann-Whitney U for between-method comparisons on run-level metrics; bootstrap CIs; distributions reported, not single points.
- **Cost reporting:** token cost per run reported for all LLM methods; B3 is compared at matched budget.

## 9. Phased Plan

| Phase | Content | Depends on |
|-------|---------|-----------|
| 0 | Freeze run contract + this spec | — |
| 1 | Evaluation infrastructure: R evaluator (fit + Qval + CA, persisted), structural checker, 4-layer stability evaluator, unified report generator, V1, V2 | 0 |
| 2 | Baselines B1/B2/B3, TSQE, expert-Q packaging | 0 |
| 3 | Perturbed item set; additional dataset onboarding | 0, V2 |
| 4 | Our methods: conform to contract, formal runs, iterate (each method version only re-runs the harness) | 1–3 |
| 5 | Full comparison matrix, headline stability × quality figure, statistics | 4 |

Critical path: V1 and V2 complete before any formal method runs (Phase 4).
