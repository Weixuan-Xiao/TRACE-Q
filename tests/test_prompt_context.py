"""Tests for src/prompt_context.py — unified prompt context builders."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.prompt_context import (
    build_scaffold_only_context_text,
    build_scaffold_transform_context_text,
    build_unified_context_text,
)
from src.scaffold_brief import scaffold_brief_to_prompt_text
from src.transform_consensus import transform_consensus_to_prompt_text

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

SCAFFOLD = {
    "proposed_k": 3,
    "clusters": [
        {
            "cluster_id": "C01",
            "provisional_skill_name": "Fraction Addition",
            "distinguishing_terms": ["fraction_addition", "simplification"],
            "item_ids": ["FS01", "FS02", "FS03"],
            "boundary_notes": ["Single dominant tag cluster"],
        },
        {
            "cluster_id": "C02",
            "provisional_skill_name": "Decimal Conversion",
            "distinguishing_terms": ["decimal_conversion"],
            "item_ids": ["FS04", "FS05"],
            "boundary_notes": ["Small cluster"],
        },
    ],
}

CONSENSUS = {
    "recommended_final_k": 2,
    "consensus_decisions": [
        {
            "cluster_id": "C01",
            "consensus_action": "keep",
            "agreement": "3/3",
            "vote_counts": {"keep": 3},
            "target_cluster_ids": [],
            "proposed_skill_names": ["Fraction Addition"],
            "notes": ["This cluster is a stable draft skill candidate."],
        },
        {
            "cluster_id": "C02",
            "consensus_action": "merge",
            "agreement": "2/3",
            "vote_counts": {"merge": 2, "keep": 1},
            "target_cluster_ids": ["C01"],
            "proposed_skill_names": ["Number Operations"],
            "notes": ["Use merged cluster group as a draft structure."],
        },
    ],
    "draft_skill_candidates": [
        {
            "name": "Fraction Addition",
            "support_count": 3,
            "source_cluster_ids": ["C01"],
        },
        {
            "name": "Number Operations",
            "support_count": 2,
            "source_cluster_ids": ["C01", "C02"],
        },
    ],
    "disputed_clusters": [],
    "summary": "test",
}

TRANSFORM_OUTPUTS = [
    {
        "expert_id": "A",
        "decisions": [
            {"cluster_id": "C01", "action": "keep", "proposed_skill_names": ["Fraction Addition"]},
            {"cluster_id": "C02", "action": "merge", "target_cluster_ids": ["C01"], "proposed_skill_names": ["Number Ops"]},
        ],
    },
    {
        "expert_id": "B",
        "decisions": [
            {"cluster_id": "C01", "action": "keep", "proposed_skill_names": ["Fraction Addition"]},
            {"cluster_id": "C02", "action": "keep", "proposed_skill_names": []},
        ],
    },
]


# ---------------------------------------------------------------------------
# Tests for build_scaffold_only_context_text
# ---------------------------------------------------------------------------

def test_scaffold_only_contains_clusters():
    text = build_scaffold_only_context_text(SCAFFOLD)
    assert "C01" in text
    assert "C02" in text
    assert "Fraction Addition" in text
    assert "Proposed K: 3" in text


def test_scaffold_only_includes_tags():
    text = build_scaffold_only_context_text(SCAFFOLD)
    assert "fraction_addition" in text


def test_scaffold_only_includes_items():
    text = build_scaffold_only_context_text(SCAFFOLD)
    assert "FS01" in text


# ---------------------------------------------------------------------------
# Tests for build_scaffold_transform_context_text
# ---------------------------------------------------------------------------

def test_transform_merges_scaffold_and_decisions():
    text = build_scaffold_transform_context_text(SCAFFOLD, TRANSFORM_OUTPUTS)
    assert "C01" in text
    assert "A=keep" in text
    assert "B=keep" in text
    assert "C02" in text
    assert "A=merge" in text


def test_transform_shows_proposed_names():
    text = build_scaffold_transform_context_text(SCAFFOLD, TRANSFORM_OUTPUTS)
    assert "Number Ops" in text


def test_transform_no_duplicate_sections():
    text = build_scaffold_transform_context_text(SCAFFOLD, TRANSFORM_OUTPUTS)
    # Should NOT have two separate titled sections for scaffold and transform
    assert text.count("STRUCTURE DISCOVERY") == 1


# ---------------------------------------------------------------------------
# Tests for build_unified_context_text
# ---------------------------------------------------------------------------

def test_unified_contains_all_clusters():
    text = build_unified_context_text(SCAFFOLD, CONSENSUS)
    assert "C01" in text
    assert "C02" in text


def test_unified_shows_consensus_actions():
    text = build_unified_context_text(SCAFFOLD, CONSENSUS)
    assert "KEEP" in text
    assert "MERGE" in text
    assert "3/3" in text
    assert "2/3" in text


def test_unified_shows_recommended_k():
    text = build_unified_context_text(SCAFFOLD, CONSENSUS)
    assert "Recommended K: 2" in text


def test_unified_merge_shows_target():
    text = build_unified_context_text(SCAFFOLD, CONSENSUS)
    # C02 merges into C01
    assert "C01" in text
    assert "MERGE" in text


def test_unified_shows_draft_candidates():
    text = build_unified_context_text(SCAFFOLD, CONSENSUS)
    assert "Draft skill candidates:" in text
    assert "Fraction Addition [support=3" in text
    assert "Number Operations [support=2" in text


def test_unified_no_duplicate_cluster_ids():
    """Each cluster_id should appear in only one header line."""
    text = build_unified_context_text(SCAFFOLD, CONSENSUS)
    header_lines = [l for l in text.split("\n") if l.startswith("- C")]
    cids = [l.split(":")[0].strip("- ").split("[")[0].strip() for l in header_lines]
    assert len(cids) == len(set(cids)), f"Duplicate cluster headers: {cids}"


def test_unified_shorter_than_separate():
    """Unified text should be shorter than two separate text blocks combined."""
    separate = (
        scaffold_brief_to_prompt_text(SCAFFOLD)
        + "\n\n---\n\n"
        + transform_consensus_to_prompt_text(CONSENSUS)
    )
    unified = build_unified_context_text(SCAFFOLD, CONSENSUS)
    assert len(unified) < len(separate), (
        f"Unified ({len(unified)} chars) should be shorter than separate ({len(separate)} chars)"
    )


def test_unified_proposed_name_dedup():
    """If consensus proposed name == scaffold name, don't repeat it."""
    text = build_unified_context_text(SCAFFOLD, CONSENSUS)
    lines = text.split("\n")
    # C01 proposed name is "Fraction Addition" same as scaffold name — should NOT show proposed name line
    c01_block = []
    capture = False
    for line in lines:
        if line.lstrip("- ").startswith("C01 "):
            capture = True
        elif line.startswith("- C") and capture:
            break
        elif capture:
            c01_block.append(line)
    c01_text = "\n".join(c01_block)
    assert "proposed name" not in c01_text, f"C01 should not repeat same name: {c01_text}"
