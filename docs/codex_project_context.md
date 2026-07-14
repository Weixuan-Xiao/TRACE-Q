# TRACE-Q Codex Project Context

**Recovered:** 2026-07-13
**Canonical working copy:** `/Users/weixuan/Desktop/Agent-Qmatrix`
**Branch at recovery:** `feature/structure-discovery-scaffold`

This document preserves useful project decisions recovered from Claude Code's
project memory and sessions. It is a dated context record, not a substitute for
current code or the frozen evaluation specification.

## 1. Research goal and claims

TRACE-Q constructs an items-by-skills binary Q-matrix for cognitive diagnostic
models from item text and solution reasoning. The method is intended to remain
text-only; response data is used only by the external evaluation harness.

The current paper plan is intentionally narrow:

- **C1 — evaluation contribution:** validate a multi-dimensional framework that
  reports generation quality and stability together.
- **C2 — method contribution:** test whether the structured multi-agent method
  improves on strong single-LLM and self-consistency baselines and approaches
  or exceeds the published expert Q when response data adjudicates the result.
- Use ablations to attribute any advantage to specific pipeline components.
- A separate traceability experiment (formerly discussed as C3) is not required
  for the current paper. Preserve intermediate decisions for auditability, but
  do not expand the experiment plan unless the owner revisits this choice.

## 2. Evaluation decisions already made

`docs/evaluation_framework.md` v1.1 is the authoritative specification. Its
durable decisions are:

- Evaluation-first development: freeze the harness, baselines, and datasets
  before finalizing the construction method.
- Run contract: `<run_id>/{Q.csv, codebook.json?, config.json}`. Evaluation must
  not inspect method internals.
- Formal K condition: each method selects K within 3-8. Fixed K=4 results are
  supplementary only.
- B3 is the serious baseline: five B2 samples, modal-K filtering, aligned cell
  voting. Report its lower token budget rather than hiding the asymmetry.
- TSQE chooses its reference K by BIC over 3-8. The expert Q is a competing
  hypothesis, not ground truth.
- No human expert recruitment in the main evaluation. Human codebook approval
  may only be a later deployment study; it must not mask auto-K instability.
- The v1.1 panel is `gpt-5.5-2026-04-23`,
  `anthropic/claude-sonnet-5`, `google/gemini-3.5-flash`, and
  `deepseek/deepseek-v4-flash`. The archived v4-pro runs are superseded.
- Additional datasets should have item text, preferably response data and a
  published Q, and differ in domain or language. Run the contamination probe
  first. Once the method is frozen, run at least 10 method runs plus relevant
  within-dataset baselines; similar raw scores across datasets alone do not
  establish generalizability.

## 3. Implemented method lines

### Original staged pipeline

The legacy design is:

`Solver -> Verifier -> Expert committee -> Supervisor align -> Supervisor consolidate -> Taggers -> Judge -> Aggregator/Export -> Auditor`

Its strengths are a clear decomposition and persisted intermediate reasoning.
Its central weakness is that independently generated codebooks must be aligned
after the fact; archived runs show substantial codebook and matrix instability.

### Structure-discovery/scaffold experiment

The current branch also implements:

`Verified dossiers -> reasoning cards -> embedding clustering -> scaffold -> cluster transformations -> consensus -> codebook -> taggers -> Q aggregation`

This line was designed to stabilize the ontology before tagging. It is not a
completed or validated replacement: the recorded development run selected K=8,
later proposed K=3, reached only partial tagger output (17/100 votes), and never
produced an evaluated final Q-matrix. Existing legacy stability and fit numbers
must not be attributed to this branch.

### Latest owner direction

The latest Claude Code session records a preference to return to the simpler
staged Agent workflow and potentially drop embedding-based clustering because
solution-text embeddings may change with reasoning style and may not represent
constructs consistently in domains such as reading. The desired alternative is
for agents to select K inside the frozen 3-8 range.

Claude Code stopped before resolving the follow-up question about old-model
provenance and bugs. Treat this as an open design direction, not a completed
branch switch. Preserve both implementations until the owner approves a
specific, testable redesign.

## 4. Current evidence and provenance cautions

- At recovery time, no formal auto-K contract run for the multi-agent method had
  been verified. Baseline generation was active; inspect run directories and
  contract validity rather than relying on historical completion counts.
- `outputs_exp/v2` and `prompt_experiment/v5_guided_fixedseed` do not record the
  model in their run metadata. Repository defaults and historical documentation
  suggest gpt-4o-mini, but the artifacts cannot prove it. Do not present their
  model attribution as certain or compare them formally with the pinned panel.
- `prompt_experiment/gpt55_K4` explicitly records GPT-5.5, but it is fixed-K and
  therefore supplementary under v1.1.
- Historical fixed-K4 diagnostics found that B2 could outperform the full
  pipeline on several agreement metrics, while the pipeline performed better
  on SRMSR and classification ARI. These results are useful for diagnosis, not
  a formal method verdict: they mix historical code, fixed K, incomplete model
  provenance, and known implementation defects.
- The worktree contains active baseline outputs and report artifacts. They are
  user data; do not clean them up or normalize git status as a side task.

## 5. Verified implementation blockers

These findings were re-checked against the current source during migration.
They must be resolved or explicitly excluded before formal method runs:

1. **Auditor reliability fields do not match.** `main_export_q.py` writes
   `full_agree`, `supermajority`, and `avg_jaccard`; `main_auditor.py` reads
   `full_agree_5`, `supermajority_4of5`, and
   `avg_pairwise_jaccard_10pairs`. Auditor-impact results from this path are not
   trustworthy.
2. **Judge voting rules are not enforced.** `src/judge.py` validates IDs and
   evidence references but does not require `auto_include` skills to remain or
   `auto_exclude` skills to stay out. An LLM can silently override the stated
   voting policy.
3. **Expert identities do not change expert prompts.** `src/expert.py` stores
   `expert_id` but does not inject it into the request. The three experts receive
   identical requests, so apparent diversity is sampling variation rather than
   designed expertise.
4. **The scaffold K instrument is biased/incomplete.** The interpretability
   input in `src/structure_discovery_embed.py` is empty while retaining weight;
   the stability score is not chance-corrected; and
   `src/transform_consensus.py` can recommend K below the formal lower bound.
5. **Temperature and provenance claims exceed what is recorded.** Models that
   reject temperature trigger a silent retry without it. Legacy runners do not
   persist all seeds, fallbacks, provider details, and token usage required for
   reproducible formal runs; scaffold runners lack a complete contract wrapper.
6. **Embedding cache provenance is incomplete.** `eval/codebook_match.py` keys
   cached embeddings by text only, not by embedding model, so changing models
   can silently reuse incompatible vectors.
7. **Configurable committee sizes are partly hard-coded.** Export labels and
   thresholds assume five taggers in several places. Do not claim arbitrary
   `n_taggers` support until the full path is tested.

Do not fix these opportunistically. For a requested fix, add a focused
regression test and make a surgical change.

## 6. Open decisions for the next method iteration

Before spending on formal method runs, resolve these explicitly:

1. Which repaired staged pipeline is the canonical candidate, and which stages
   are retained or removed?
2. How will agents select K in 3-8 using a reproducible rule that transfers
   across domains?
3. Where, if anywhere, should heterogeneous model committees be used? Prior
   review supports testing them for discrete tagging/judging votes, but not
   assuming they improve open-ended codebook generation. Any heterogeneous arm
   needs a matching heterogeneous B3 control to separate structure from model
   diversity.
4. What is the smallest anchor-model shakedown that demonstrates contract
   compliance and improved K/codebook stability before the full panel runs?

## 7. Recovered sources

The migration consulted the repository, Git history, the global Claude rules,
five Claude project-memory files, and the relevant project session timeline.
Raw session logs, user biography, API credentials, `.env` values, and proxy
settings were deliberately not copied into the repository.
