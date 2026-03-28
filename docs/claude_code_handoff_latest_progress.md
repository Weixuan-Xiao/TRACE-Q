# Claude Code Handoff: Latest Progress on TRACE-Q Structure-Discovery Branch

## 1. Project purpose

TRACE-Q is a multi-agent LLM pipeline for constructing a **Q-matrix directly from item text and solution reasoning**, without relying on response data.

The current research goal is not just to produce a plausible Q-matrix, but to produce a **stable, transparent, and auditable skill codebook** and a downstream Q-matrix whose uncertainty can be explicitly analyzed.

The main problem discovered in the earlier pipeline is **instability of the skills codebook**:
- when experts generate codebooks independently from the same verified dossiers,
- even if `K` is fixed,
- skill boundaries, naming, and granularity still drift across runs.

The new branch introduces a **structure-discovery-first design** so that later agents start from a shared scaffold instead of free ontology generation.

---

## 2. Branches and baseline

### Baseline branch
- Base branch: `old`

### Experimental refactor branch
- Working branch: `feature/structure-discovery-scaffold`

The `old` branch mainly follows this logic:

`Solver -> Verifier -> Expert Committee -> Supervisor Align -> Supervisor Consolidate -> Taggers`

Problem with the old branch:
- experts start from the same dossiers but still generate codebooks independently;
- supervisor must do too much semantic alignment and consolidation from scratch;
- fixing `K` does **not** sufficiently stabilize the ontology.

---

## 3. Main methodological change in the new branch

The new branch moves from:

**free generation -> align -> consolidate**

to:

**structure discovery -> cluster transformation -> consensus -> codebook induction -> Q aggregation**

### New high-level idea
1. Build **reasoning cards** from item text + solution summaries + step traces.
2. Use **structure discovery** to cluster items in a shared reasoning space.
3. Convert clusters into a **scaffold brief**.
4. Ask transformer experts to decide for each cluster whether it should be:
   - keep
   - merge
   - split
   - relabel
5. Build a **structured consensus layer** from those transformation outputs.
6. Use scaffold + consensus to guide final codebook induction.
7. After taggers vote, aggregate votes into:
   - final Q-matrix
   - cell/item uncertainty reports
   - stability summary

Important methodological principle:
- `K_cluster` does **not** have to equal final `K_skill`.
- The system explicitly allows:
  - `1 cluster -> 1 skill`
  - `many clusters -> 1 skill`
  - `1 cluster -> many skills`

---

## 4. What has already been implemented in this branch

## 4.1 Structure discovery layer

### Reasoning cards
Implemented files:
- `schemas/reasoning_card.py`
- `src/reasoning_card.py`

Purpose:
- Normalize dossier information into a compact intermediate representation for clustering.
- Current fields include:
  - `item_id`
  - `stem_text`
  - `solution_summary`
  - `step_texts`
  - `operation_tags`
  - `structural_signature`

### Embedding-first structure discovery
Implemented files:
- `src/embedding_client.py`
- `src/structure_discovery_embed.py`
- `main_structure_discovery_embed.py`

Purpose:
- Convert reasoning cards into embedding-based representations.
- Search candidate `K` values using hierarchical clustering over reasoning-card embeddings.
- Score candidate partitions using metrics such as:
  - stability
  - silhouette
  - interpretability proxy
  - balance
- Write out:
  - reasoning cards
  - candidate `K` table
  - scaffold brief

There is also a TF-IDF / non-embedding fallback path in the structure-discovery utilities, mainly for robustness or debugging.

### Scaffold brief construction
Implemented files:
- `schemas/scaffold_brief.py`
- `src/scaffold_from_clusters.py`
- `src/scaffold_brief.py`

Purpose:
- Turn cluster outputs into a prompt-ready scaffold.
- Current scaffold includes cluster-level information such as:
  - cluster id
  - provisional skill name
  - operation tags
  - representative items
  - boundary notes
  - item ids

---

## 4.2 Cluster transformation layer

### Transformer expert stage
Implemented files:
- `schemas/cluster_transform.py`
- `src/cluster_transformer.py`
- `main_cluster_transform.py`

Purpose:
- Given the scaffold, each transformer expert reviews each cluster and outputs structured decisions:
  - keep
  - merge
  - split
  - relabel
- Each expert also proposes draft skills linked to source clusters.

This is already more structured than simply prompting experts to generate a full codebook from scratch.

---

## 4.3 Transformation consensus layer

### Structured consensus stage
Implemented files:
- `schemas/transform_consensus.py`
- `src/transform_consensus.py`
- `main_transform_consensus.py`

Purpose:
- Build a consensus summary from multiple transformer outputs.
- Current outputs include:
  - `consensus_decisions`
  - `draft_skill_candidates`
  - `disputed_clusters`
  - `recommended_final_k`
  - summary text

This is important because it begins to make the pipeline less dependent on unstructured prompt interpretation.

---

## 4.4 Consensus-aware codebook induction

### Consensus-aware taxonomist stage
Implemented file:
- `main_taxonomist_consensus.py`

Purpose:
- Read:
  - scaffold brief
  - transformation consensus
- Inject both into expert/supervisor prompts.
- If the user does **not** manually set `target_k_exact`, this stage can use:
  - `recommended_final_k`

This is the current best version of codebook induction in the new branch.

However, note an important limitation:
- the consensus layer is **partially operationalized**, but still not fully enforced as a hard programmatic constraint.
- At present, it is still largely consumed through prompt injection, plus `recommended_final_k`.
- There is more room to convert consensus into stronger structural constraints.

---

## 4.5 End-to-end pipeline entrypoint

Implemented file:
- `main_pipeline_consensus.py`

Purpose:
- Run the end-to-end new path:
  1. structure discovery
  2. cluster transformation
  3. transform consensus
  4. consensus-aware taxonomist
  5. optional taggers
  6. optional Q aggregation

This is the intended end-to-end experimental pipeline for the new branch.

---

## 4.6 Post-tagger Q aggregation and uncertainty reporting

Implemented files:
- `src/q_aggregate.py`
- `main_q_aggregate.py`

Purpose:
- Take multiple tagger vote files and aggregate them into:
  - final Q-matrix
  - cell-level uncertainty report
  - item-level uncertainty report
  - stability summary

This is crucial because the project goal includes **stability analysis**, not just a final hard Q-matrix.

---

## 5. Current pipeline summary

The intended new path is now:

`Verified dossiers`
-> `Reasoning cards`
-> `Embedding-based structure discovery`
-> `Scaffold brief`
-> `Cluster transformation review`
-> `Transformation consensus`
-> `Consensus-aware taxonomist`
-> `Final codebook`
-> `Taggers (optional)`
-> `Q aggregation + uncertainty summary (optional)`

---

## 6. Main problem right now

The current branch is **methodologically much stronger** than the old branch, but it is starting to become **cognitively heavy for agents**.

The biggest concern is not simply that there are more stages.
The bigger concern is:

> too much information is still being passed forward to later agents.

This can reduce stability because later experts/supervisors may receive:
- large verified dossier information,
- scaffold summaries,
- transformation outputs,
- consensus information,
- domain guides,
- long prompts,
all at once.

This is likely to create attention drift and unstable behavior.

---

## 7. The most important optimization target for Claude Code

### Core recommendation
Do **not** primarily optimize by deleting stages.

Instead, optimize by **shrinking the input packet for each agent**.

The goal should be:

**modular pipeline + minimal agent context**

rather than:

**short pipeline + overloaded prompts**

### Recommended optimization direction

#### A. Introduce minimal packets for each stage
The most important next refactor is a **context slimming refactor**.

Only early stages should see raw dossier-level information.
Later stages should see only compressed summaries.

Suggested rule:
- Early, machine-heavy stages:
  - dossiers
  - embeddings
  - clustering
  - vote aggregation
- Later, summary-heavy stages:
  - cluster dossier
  - transform consensus table
  - draft skill sheet
  - final codebook card

#### B. Reduce what later agents see
For example:
- transformer experts should not read all raw dossiers;
- taxonomist experts should not read full raw dossier collections;
- supervisor should preferably see only:
  - draft skill candidates
  - disputed clusters
  - concise boundary notes

#### C. Split scaffold into two versions
Recommended:
- **brief scaffold** for agents
- **full scaffold** for debugging/human inspection

Most agents should consume only the brief scaffold.

#### D. Convert consensus from prompt-text reference to stronger structural input
Currently consensus is partly operationalized but still mostly passed through prompts.

Potential improvement:
- create programmatic pre-groupings based on consensus;
- treat strong keep/merge/split decisions as draft structure;
- make later stages review only disputed parts rather than re-reading everything.

#### E. Keep downstream tagger context narrow
Taggers should likely see only:
- final codebook
- representative examples per skill
- near-miss / boundary notes

They should **not** need the whole history from structure discovery to consensus.

---

## 8. Concrete questions Claude Code should optimize

Claude Code should focus on these practical questions:

1. **How can the branch be simplified without losing the methodological advantages?**
2. **How can each stage receive a smaller, more stable input packet?**
3. **How can transformation consensus become more programmatic and less prompt-dependent?**
4. **How can scaffold / consensus / draft skills be represented in a compact way for later agents?**
5. **How can the taxonomist stage be restructured so expert and supervisor each see only what they truly need?**
6. **How can tagger prompts be shortened while preserving boundary awareness?**
7. **How can the full pipeline be kept auditable while reducing prompt size and agent overload?**

---

## 9. Suggested immediate optimization priorities

Recommended order for optimization:

### Priority 1
Refactor the branch around **minimal stage packets**.

### Priority 2
Make the consensus layer more structurally binding.

### Priority 3
Reduce duplication and overlap among:
- scaffold summary
- transform summary
- consensus summary
- taxonomist prompt inputs

### Priority 4
Unify the new branch around a single canonical path:
- official structure discovery runner
- official consensus-aware taxonomist runner
- official end-to-end runner

### Priority 5
Optionally improve how final uncertainty information is surfaced for experiments and paper writing.

---

## 10. Short summary for Claude Code

This branch is trying to solve **skill codebook instability** in TRACE-Q by replacing free expert ontology generation with a **shared structure-discovery scaffold**, followed by **cluster transformation review**, **consensus building**, and **consensus-aware codebook induction**.

The current branch already implements most of that pipeline, including post-tagger Q aggregation.

The main optimization challenge is now:

> preserve the new methodological strength, but make the branch less bloated by reducing how much information each agent must read.

Claude Code should therefore focus on:
- context slimming,
- better structured intermediate packets,
- stronger use of consensus as a machine-readable constraint,
- and simplification of the agent-facing interface.
