"""Score semantic roles and table/grid availability against confirmed PDF labels."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
IR_DIR = ROOT / "results" / "text-structure" / "ir"
ANNOTATIONS = ROOT / "results" / "text-structure" / "manual-annotations"
SAMPLE_IDS = ["SELF-001", "SELF-002", "SELF-003"]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().casefold()


def iou(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right or len(left) != 4 or len(right) != 4:
        return 0.0
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_left = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    area_right = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = area_left + area_right - intersection
    return intersection / union if union else 0.0


def expected_type(label: str) -> str:
    return {
        "title": "heading",
        "heading": "heading",
        "paragraph": "paragraph",
        "table": "table",
        "footnote": "footnote",
        "footer": "footer",
    }.get(label, label)


def load(sample_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    ir = json.loads((IR_DIR / f"{sample_id}.json").read_text(encoding="utf-8"))
    gold = json.loads((ANNOTATIONS / f"{sample_id}.json").read_text(encoding="utf-8"))
    return ir, gold


def score(sample_id: str) -> dict[str, Any]:
    ir, gold = load(sample_id)
    predicted = ir.get("elements", [])
    units = gold.get("units", [])
    matched: list[dict[str, Any]] = []
    used: set[str] = set()
    for unit in units:
        unit_text = normalize(unit.get("text", ""))
        candidates = [
            element for element in predicted
            if element["element_id"] not in used and unit_text and normalize(element.get("text", "")) == unit_text
        ]
        if not candidates:
            candidates = [
                element for element in predicted
                if element["element_id"] not in used and iou(unit.get("bbox"), element.get("bbox")) >= 0.5
            ]
        candidate = max(candidates, key=lambda item: iou(unit.get("bbox"), item.get("bbox")), default=None)
        if candidate:
            used.add(candidate["element_id"])
        matched.append({"gold": unit, "predicted": candidate})

    role_matches = sum(
        item["predicted"] is not None
        and item["predicted"].get("element_type") == expected_type(item["gold"].get("label", ""))
        for item in matched
    )
    bbox_covered = sum(
        any(iou(unit.get("bbox"), element.get("bbox")) >= 0.5 for element in predicted)
        for unit in units
    )
    table_gold = gold.get("table_grids", [])
    table_pred = [element for element in predicted if element.get("element_type") == "table"]
    grid_results = []
    for grid in table_gold:
        grid_results.append({
            "table_id": grid.get("table_id"),
            "gold_shape": [grid.get("rows"), grid.get("columns")],
            "predicted_table_count": len(table_pred),
            "predicted_cell_count": sum(len(table.get("children_ids", [])) for table in table_pred),
            "grid_available": bool(table_pred),
            "cell_grid_available": any(table.get("children_ids") for table in table_pred),
        })
    return {
        "experiment_id": "TECH-STRUCT-003-R01",
        "sample_id": sample_id,
        "parser": ir.get("parser_name"),
        "gold_units": len(units),
        "predicted_elements": len(predicted),
        "matched_units": sum(item["predicted"] is not None for item in matched),
        "bbox_coverage": bbox_covered / len(units) if units else None,
        "semantic_role_recall": role_matches / len(units) if units else None,
        "footnote_gold": sum(unit.get("label") == "footnote" for unit in units),
        "footnote_semantic_matches": sum(
            item["gold"].get("label") == "footnote"
            and item["predicted"] is not None
            and item["predicted"].get("element_type") == "footnote"
            for item in matched
        ),
        "footer_gold": sum(unit.get("label") == "footer" for unit in units),
        "footer_semantic_matches": sum(
            item["gold"].get("label") == "footer"
            and item["predicted"] is not None
            and item["predicted"].get("element_type") == "footer"
            for item in matched
        ),
        "tables": grid_results,
        "boundary": "Role and grid scores measure this low-level adapter; they are not a parser-wide accuracy claim.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="append", choices=SAMPLE_IDS, dest="samples")
    args = parser.parse_args()
    samples = args.samples or SAMPLE_IDS
    report = {
        "experiment_id": "TECH-STRUCT-003-R01",
        "scope": "confirmed PDF semantic roles and table grid availability",
        "outputs": [score(sample_id) for sample_id in samples],
        "boundary": "No OCR metrics; no claim for unannotated DOCX, Markdown, or TXT semantics.",
    }
    out = IR_DIR / "relation-score.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
