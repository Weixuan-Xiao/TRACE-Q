# Structure Discovery Runner Guide

## Recommended entrypoint

Use:

- `main_structure_discovery_embed.py`

This is the **official embedding-first structure discovery runner** for the scaffold pipeline.

It:
1. builds reasoning cards from verified dossiers;
2. searches candidate `K` values using embedding-based hierarchical clustering;
3. optionally falls back to the TF-IDF backend if embeddings fail;
4. writes the scaffold brief used by later taxonomist stages.

## Legacy / experimental entrypoints

- `main_structure_discovery.py`
  - early heuristic baseline
- `main_structure_discovery_cluster.py`
  - TF-IDF candidate-K clustering runner

These are still useful for debugging and ablation, but they are not the recommended default.

## Typical usage

```bash
python main_structure_discovery_embed.py \
  --input outputs/step2_verifier_verified_item_dossiers.jsonl \
  --out_cards outputs/step2_5_reasoning_cards.jsonl \
  --out_candidates outputs/step2_5_cluster_candidates.json \
  --out_scaffold outputs/step2_5_scaffold_brief.json
```

## Environment

Embedding mode expects:

- `OPENAI_API_KEY`
- `OPENAI_EMBEDDING_MODEL`

The runner also accepts:

- `--embedding_model` to override the env var
- `--force_method tfidf` to force the non-embedding backend
- `--fallback_method none` to disable fallback

## Output files

- `step2_5_reasoning_cards.jsonl`
- `step2_5_cluster_candidates.json`
- `step2_5_scaffold_brief.json`

## Downstream stages

Recommended next steps:

1. `python main_cluster_transform.py`
2. `python main_taxonomist_transform.py`
