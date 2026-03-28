# Structure Discovery Pipeline Refactor Plan

Base branch: `old`
Working branch: `feature/structure-discovery-scaffold`

## Goal

Insert a **Structure Discovery** stage between verifier and taxonomist so the skill codebook is generated from a shared scaffold rather than from three fully independent expert generations.

## Revised pipeline

1. `main.py`
   - Solver builds item dossiers.
2. verifier stage
   - Produces verified dossiers.
3. `main_structure_discovery.py` **(new)**
   - Builds reasoning cards from verified dossiers.
   - Generates embeddings.
   - Runs candidate clustering.
   - Evaluates candidate `K` values.
   - Produces a scaffold brief for downstream agents.
4. `main_taxonomist.py` **(modify)**
   - Loads scaffold brief.
   - Experts work from the same scaffold.
   - Supervisor performs audit/refinement rather than large-scale consolidation from scratch.
5. `main_taggers.py` **(modify)**
   - Reads final codebook plus scaffold examples/boundary notes.
6. aggregation stage
   - Produces final Q-matrix and uncertainty summary.

## Proposed new outputs

- `outputs/step2_5_reasoning_cards.jsonl`
- `outputs/step2_5_cluster_candidates.json`
- `outputs/step2_5_cluster_stability.json`
- `outputs/step2_5_scaffold_brief.json`
- `outputs/step2_5_umap.png`

## Proposed new modules

### `src/reasoning_card.py`
Build a normalized reasoning representation per item using:
- item stem
- solver summary
- solution steps
- optional abstracted operation tags

### `src/structure_discovery.py`
Main orchestration for:
- embedding generation
- distance computation
- hierarchical clustering
- candidate partition generation

### `src/cluster_selection.py`
Evaluate candidate `K` values using:
- stability across seeds / perturbations
- minimum cluster size
- interpretability proxy
- redundancy / overlap checks

### `src/scaffold_brief.py`
Transform selected clusters into a prompt-ready scaffold brief containing:
- proposed `K`
- cluster ids
- representative items
- keyword summaries
- common solution patterns
- boundary-risk notes

## Candidate changes to existing files

### `main_taxonomist.py`
- Add `--scaffold_brief` argument.
- Inject scaffold brief into Expert and Supervisor prompts.
- Switch expert task from free codebook generation to scaffold-based keep / merge / split / relabel decisions.

### `src/expert.py`
- Add scaffold-aware input payload.
- Change validation logic so Experts can recommend:
  - keep
  - merge
  - split
  - relabel
- Preserve exact-`K` mode as an option, but default to scaffold-informed recommendation.

### `src/supervisor.py`
- Reduce emphasis on cross-expert semantic alignment from scratch.
- Add focus on:
  - boundary clarification
  - redundancy removal
  - completeness audit
  - final skill list derivation from scaffold transformations

### `main_taggers.py`
- Optionally inject scaffold examples and near-miss items with the codebook.

## Important methodological rule

`K_cluster` is not required to equal final `K_skill`.

Allowed transformations from cluster scaffold to final skill list:
- `1 cluster -> 1 skill`
- `many clusters -> 1 skill`
- `1 cluster -> many skills`

This should be documented explicitly in prompts and method write-up.

## Suggested first implementation order

1. Add `main_structure_discovery.py`
2. Add scaffold brief JSON schema
3. Modify `main_taxonomist.py` to read scaffold brief
4. Update Expert prompt contract
5. Update Supervisor prompt contract
6. Update Tagger context injection

## Discussion items still open

1. Embedding input:
   - item only
   - item + solution summary
   - item + solution summary + step trace
2. Distance type:
   - semantic only
   - structural only
   - weighted fusion
3. `K` selection protocol:
   - which stability statistics to compute
   - whether to use downstream codebook stability as part of model selection
4. Cluster-to-skill induction template:
   - exact dossier fields
   - boundary examples
   - near-miss examples
