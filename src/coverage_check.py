"""
Coverage check for codebook quality.

Estimates how many items each skill would cover by matching skill
inclusion/exclusion criteria against dossier solution steps.
Flags skills that violate identifiability constraints:
  - Upper bound: skill covers > threshold fraction of items (no discriminative power)
  - Lower bound: skill covers < min_items items (not identifiable in CDM)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

JsonDict = Dict[str, Any]

# Defaults based on CDM identifiability theory
DEFAULT_MAX_COVERAGE = 0.90  # >90% items → too broad
DEFAULT_MIN_ITEMS = 3        # <3 items → not identifiable


def estimate_skill_coverage(
    codebook: JsonDict,
    dossiers: List[JsonDict],
) -> Dict[str, List[str]]:
    """Estimate which items each skill covers using exclusion-based heuristic.

    Strategy: for each skill, assume it covers ALL items, then remove items
    that match exclusion criteria. This avoids false positives from overly
    broad keyword matching on inclusion criteria.

    Falls back to example-only estimation when exclusion criteria are absent.

    Returns: {skill_id: [item_id, ...]}
    """
    skills = codebook.get("skills", [])

    # Build item lookup: item_id → solution step texts joined
    item_steps: Dict[str, str] = {}
    item_stems: Dict[str, str] = {}
    for d in dossiers:
        item_id = d.get("item_id", d.get("item", {}).get("item_id", ""))
        solver = d.get("solver", {})
        steps = solver.get("solution_steps", [])
        step_text = " ".join(s.get("text", "") for s in steps).lower()
        item_steps[item_id] = step_text
        item_stems[item_id] = d.get("item", {}).get("stem_text", "").lower()

    all_item_ids = sorted(item_steps.keys())
    coverage: Dict[str, List[str]] = {}

    for skill in skills:
        sid = skill.get("skill_id", "")
        exclusion = skill.get("exclusion_criteria", [])
        inclusion = skill.get("inclusion_criteria", [])

        # Start with items from examples (guaranteed covered)
        example_items = set()
        for ex in skill.get("examples", []):
            ex_item = ex.get("item_id", "")
            if ex_item in item_steps:
                example_items.add(ex_item)

        # Use inclusion criteria to find additional covered items
        # Extract specific operational phrases (multi-word only, avoid generic terms)
        inc_phrases = _extract_specific_phrases(inclusion)
        exc_phrases = _extract_specific_phrases(exclusion)

        covered = set(example_items)
        for item_id in all_item_ids:
            if item_id in covered:
                continue
            step_text = item_steps[item_id]
            stem_text = item_stems[item_id]
            full_text = stem_text + " " + step_text

            # Item matches if any inclusion phrase matches
            # AND no exclusion phrase matches
            inc_match = any(p in full_text for p in inc_phrases) if inc_phrases else False
            exc_match = any(p in full_text for p in exc_phrases) if exc_phrases else False

            if inc_match and not exc_match:
                covered.add(item_id)

        coverage[sid] = sorted(covered)

    return coverage


def _extract_specific_phrases(criteria: List[str]) -> List[str]:
    """Extract specific multi-word phrases from criteria text.

    Only extracts phrases that are specific enough to be useful for matching.
    Avoids single generic words that would match everything.
    """
    # Multi-word phrases that indicate specific operations
    SPECIFIC_PHRASES = [
        "common denominator", "lcd", "lcm",
        "equivalent fraction", "borrow", "regroup",
        "improper fraction", "mixed number",
        "lowest terms", "whole number",
        "whole part", "fractional part",
        "zero fraction", "zero-fraction",
        "improper fractional part", "normalized",
        "decompos",  # decompose/decomposition
    ]

    found = []
    for criterion in criteria:
        criterion_lower = criterion.lower()
        for phrase in SPECIFIC_PHRASES:
            if phrase in criterion_lower and phrase not in found:
                found.append(phrase)

    return found


def _detect_domain_core_skills(codebook: JsonDict) -> List[str]:
    """Detect skills that describe the domain's core operation.

    A skill is likely universal if its definition describes the same action
    as the codebook's domain description (e.g., "subtract" in a subtraction domain)
    AND its exclusion criteria only exclude other operations (step-level),
    not specific item conditions (item-level).
    """
    domain = codebook.get("domain", "").lower()
    skills = codebook.get("skills", [])

    # Extract domain core verbs (first verb-like words in domain description)
    domain_verbs = []
    for word in ["subtract", "add", "multiply", "divide", "solve", "factor",
                 "simplif", "compar", "convert", "evaluat", "comput", "calculat"]:
        if word in domain:
            domain_verbs.append(word)

    if not domain_verbs:
        return []

    suspect_sids = []
    for skill in skills:
        sid = skill.get("skill_id", "")
        defn = skill.get("definition", "").lower()
        name = skill.get("name", "").lower()

        # Check if skill NAME contains the domain's core verb — the name
        # describes the skill's primary action. Matching on definition alone
        # catches incidental mentions (e.g., "subtraction-ready form").
        matches_domain_verb = any(v in name for v in domain_verbs)
        if not matches_domain_verb:
            continue

        # Check if exclusion criteria contain item-level conditions.
        # Step-level exclusions say "do not tag for X operation" — they only
        # exclude specific steps, not entire items.
        # Item-level exclusions say "when denominators are already the same" —
        # they exclude entire items from needing this skill.
        exclusions = skill.get("exclusion_criteria", [])
        has_item_level_exclusion = False
        for exc in exclusions:
            exc_lower = exc.lower()
            # Item-level exclusion: conditions about the ITEM's structure
            if any(phrase in exc_lower for phrase in [
                "when denominators are already",
                "when denominators are the same",
                "when the item ",
                "only applies when",
                "when the problem ",
                "when both fractions already",
            ]):
                has_item_level_exclusion = True
                break

        if not has_item_level_exclusion:
            suspect_sids.append(sid)

    return suspect_sids


def check_coverage_violations(
    codebook: JsonDict,
    dossiers: List[JsonDict],
    max_coverage: float = DEFAULT_MAX_COVERAGE,
    min_items: int = DEFAULT_MIN_ITEMS,
) -> Tuple[List[JsonDict], Dict[str, List[str]]]:
    """Check codebook for coverage violations.

    Uses two strategies:
    1. Heuristic coverage estimation (keyword matching)
    2. Domain-core skill detection (structural analysis of definitions)

    Returns:
        violations: list of {skill_id, skill_name, issue, n_items, n_total, item_ids}
        coverage: full coverage dict for reference
    """
    coverage = estimate_skill_coverage(codebook, dossiers)
    n_total = len(dossiers)
    all_item_ids = sorted(
        d.get("item_id", d.get("item", {}).get("item_id", "")) for d in dossiers
    )
    skills = codebook.get("skills", [])
    skill_map = {s["skill_id"]: s.get("name", "") for s in skills}
    skill_map_full = {s["skill_id"]: s for s in skills}

    # Detect domain-core skills (likely universal even if heuristic misses them)
    domain_core_sids = _detect_domain_core_skills(codebook)

    violations: List[JsonDict] = []

    for sid, covered_items in coverage.items():
        n_covered = len(covered_items)
        ratio = n_covered / n_total if n_total > 0 else 0

        is_domain_core = sid in domain_core_sids

        if ratio > max_coverage or is_domain_core:
            detail = (
                f"Covers {n_covered}/{n_total} items ({ratio:.0%}) by estimation"
            )
            if is_domain_core:
                detail += (
                    ". Also detected as a DOMAIN-CORE skill — its definition describes "
                    "the domain's primary operation, making it likely universal"
                )
            detail += ". This skill likely has no discriminative power."
            violations.append({
                "skill_id": sid,
                "skill_name": skill_map.get(sid, ""),
                "issue": "too_broad",
                "detail": detail,
                "n_items": n_covered,
                "n_total": n_total,
                "item_ids": covered_items if ratio > max_coverage else all_item_ids,
            })
        # NOTE: too_narrow (< min_items) is NOT checked here because the
        # heuristic underestimates coverage. The >=3 items identifiability
        # constraint should be enforced post-tagging with the actual Q-matrix.

    return violations, coverage


def format_violations_feedback(violations: List[JsonDict]) -> str:
    """Format violations into a feedback string for Expert re-run."""
    if not violations:
        return ""

    lines = [
        "## Coverage Violations from Previous Round",
        "",
        "The following skills from the previous codebook failed identifiability checks. "
        "You MUST redesign your codebook to avoid these problems:",
        "",
    ]

    for v in violations:
        sid = v["skill_id"]
        name = v["skill_name"]
        issue = v["issue"]
        detail = v["detail"]

        if issue == "too_broad":
            lines.append(f"- **{sid} ({name})**: TOO BROAD — {detail}")
            lines.append(f"  → Do NOT create a single skill that covers all or nearly all items. "
                         f"Split this into finer sub-skills that discriminate between items.")
        elif issue == "too_narrow":
            lines.append(f"- **{sid} ({name})**: TOO NARROW — {detail}")
            lines.append(f"  → Merge this with a related skill or broaden its scope.")
        lines.append("")

    lines.append("Remember: each skill must cover at least 3 items and no skill should cover more than 90% of items.")
    lines.append("")

    return "\n".join(lines)
