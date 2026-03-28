from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from src.codebook_utils import extract_skill_ids

JsonDict = Dict[str, Any]


def _binary_entropy(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def load_vote_rows(votes_dir: str | Path) -> list[JsonDict]:
    rows: list[JsonDict] = []
    for path in sorted(Path(votes_dir).glob("*.jsonl")):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    return rows


def collect_vote_matrix(
    *,
    rows: list[JsonDict],
    skill_ids: Iterable[str],
) -> tuple[dict[str, dict[str, list[int]]], list[str]]:
    ordered_skills = sorted({str(s).strip() for s in skill_ids if str(s).strip()})
    matrix: dict[str, dict[str, list[int]]] = defaultdict(lambda: {sid: [] for sid in ordered_skills})

    for row in rows:
        item_id = str(row.get("item_id", "")).strip()
        vote = row.get("vote", {}) if isinstance(row.get("vote"), dict) else {}
        chosen = {
            str(skill.get("skill_id", "")).strip()
            for skill in vote.get("skills", [])
            if str(skill.get("skill_id", "")).strip()
        }
        for sid in ordered_skills:
            matrix[item_id][sid].append(1 if sid in chosen else 0)
    return matrix, ordered_skills


def finalize_q_matrix(
    *,
    matrix: dict[str, dict[str, list[int]]],
    skill_ids: list[str],
    decision_threshold: float = 0.5,
) -> tuple[list[JsonDict], list[JsonDict], list[JsonDict], JsonDict]:
    q_rows: list[JsonDict] = []
    cell_rows: list[JsonDict] = []
    item_rows: list[JsonDict] = []

    skill_entropy: Counter[str] = Counter()
    skill_cell_count: Counter[str] = Counter()
    total_cell_agreement = 0.0
    total_cells = 0

    for item_id in sorted(matrix):
        row_out: JsonDict = {"item_id": item_id}
        item_borderline = 0
        item_mean_agreement = 0.0

        for sid in skill_ids:
            votes = matrix[item_id].get(sid, [])
            n = len(votes)
            yes = sum(votes)
            p = yes / n if n else 0.0
            final_value = 1 if p > decision_threshold or math.isclose(p, decision_threshold) else 0
            agreement = max(p, 1 - p)
            entropy = _binary_entropy(p)
            disputed = 1 if 0.4 <= p <= 0.6 else 0
            if disputed:
                item_borderline += 1

            row_out[sid] = final_value
            cell_rows.append(
                {
                    "item_id": item_id,
                    "skill_id": sid,
                    "votes_for_one": yes,
                    "num_votes": n,
                    "vote_proportion": round(p, 4),
                    "final_value": final_value,
                    "agreement": round(agreement, 4),
                    "entropy": round(entropy, 4),
                    "disputed": disputed,
                }
            )
            item_mean_agreement += agreement
            total_cell_agreement += agreement
            total_cells += 1
            skill_entropy[sid] += entropy
            skill_cell_count[sid] += 1

        q_rows.append(row_out)
        item_rows.append(
            {
                "item_id": item_id,
                "mean_cell_agreement": round(item_mean_agreement / max(len(skill_ids), 1), 4),
                "num_borderline_cells": item_borderline,
                "num_active_skills": sum(int(row_out[sid]) for sid in skill_ids),
            }
        )

    skill_rows = []
    for sid in skill_ids:
        skill_rows.append(
            {
                "skill_id": sid,
                "mean_entropy": round(skill_entropy[sid] / max(skill_cell_count[sid], 1), 4),
                "num_cells": skill_cell_count[sid],
            }
        )

    summary = {
        "num_items": len(q_rows),
        "num_skills": len(skill_ids),
        "mean_cell_agreement": round(total_cell_agreement / max(total_cells, 1), 4),
        "num_disputed_cells": sum(int(row["disputed"]) for row in cell_rows),
        "decision_threshold": decision_threshold,
        "skill_uncertainty_summary": skill_rows,
    }
    return q_rows, cell_rows, item_rows, summary
