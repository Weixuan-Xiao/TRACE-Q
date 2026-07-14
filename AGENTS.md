# AGENTS.md

This file is the durable project instruction entry point for Codex. Read it
before changing the repository, then read `docs/codex_project_context.md` for
the recovered project history and current open decisions.

## Collaboration and change discipline

- Communicate with the project owner in Chinese unless another language is
  requested. Keep code, identifiers, and repository documentation consistent
  with the surrounding files.
- Before implementation, state assumptions and a short, verifiable plan. If a
  decision would change the research design or canonical method, surface the
  alternatives instead of choosing silently.
- Make the smallest change that solves the requested problem. Do not refactor,
  reformat, or clean adjacent code unless it is necessary for that problem.
- Preserve user changes and experiment artifacts. The worktree may contain
  active or completed runs; do not delete, overwrite, move, or regenerate them
  without explicit authorization.
- Verify the requested outcome. For bugs, reproduce the failure when practical;
  for code changes, run the narrow tests first and the full suite when risk
  warrants it.
- Never commit secrets or copy `.env`, API keys, proxy settings, or raw private
  conversation logs into the repository.

## Project purpose

TRACE-Q constructs Q-matrices for cognitive diagnostic models from item text
and solution reasoning. Its intended contribution is an evaluation-first,
multi-agent method whose generation quality and cross-run stability can be
compared fairly with single-LLM and reference baselines.

The construction method must remain text-only during generation. Response data
belongs to the evaluation side and must not leak into method prompts or method
selection logic.

## Source precedence

Use sources in this order when they disagree:

1. Current code, tests, and run metadata.
2. `docs/evaluation_framework.md`, currently frozen at v1.1.
3. `docs/codex_project_context.md`, a dated status and decision record.
4. Historical documents such as `README.md`, `eval/README.md`,
   `docs/method_summary.md`, `docs/claude_code_handoff_latest_progress.md`, and
   `docs/TRACE-Q-experiment-spec.md`.

Historical documents contain stale commands and claims. In particular, some
still describe fixed K=4, DeepSeek v4-pro, guaranteed temperature=0 behavior,
or the structure-discovery branch as canonical. Do not repeat those claims
without checking the frozen framework and current implementation.

## Frozen evaluation invariants

- The evaluation harness is method-agnostic. Each run must conform to
  `<run_id>/{Q.csv, codebook.json?, config.json}`; validate it with
  `python -m eval.contract <runs_root>`.
- The sole formal generation condition is automatic K selection within 3-8.
  Fixed-K results are supplementary and must not be mixed into the formal
  comparison.
- Quality and stability are reported jointly. The primary quality dimensions
  are structural validity, conditional empirical fit, TSQE agreement, expert-Q
  agreement, and classification ARI. Stability is measured at K, codebook,
  matrix, and classification layers.
- Use at least 10 independent runs per method/model/dataset for stability
  claims. A single run cannot support a stability or generalizability claim.
- The pinned v1.1 model panel is GPT-5.5, Claude Sonnet 5, Gemini 3.5 Flash, and
  DeepSeek v4-flash. B3 uses N=5. Do not re-anchor, alter metrics, or change the
  panel silently; changes require an explicit framework version amendment.
- The published expert Q and TSQE are competing references, not ground truth.
  Respect the circularity exclusions described in the frozen framework.

## Method direction is not settled

There are two implemented lines: the original staged multi-agent pipeline and
the experimental embedding-based structure-discovery/scaffold pipeline. The
owner's latest recorded preference is to return to a clear staged agent
workflow, let agents choose K within 3-8, and potentially abandon embedding
clustering because its construct validity may not transfer across domains.

This is a direction under evaluation, not an implemented or frozen decision.
Do not treat the scaffold path as canonical, and do not delete it. Before a
method redesign, re-check the known blockers and agree on the smallest
testable method variant with the owner.

## Verification commands

Use the repository virtual environment when available:

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m eval.contract <runs_root>
.venv/bin/python -m eval.report --runs_root <runs_root> --out <report_dir> \
  --expert_q data/expert_q_tatsuoka.csv
```

The report command may invoke R/GDINA and embedding APIs. Do not run costly or
networked formal experiments merely to verify a local code or documentation
change.
