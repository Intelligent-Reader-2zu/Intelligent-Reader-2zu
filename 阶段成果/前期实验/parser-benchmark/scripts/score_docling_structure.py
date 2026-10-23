"""Compare Docling IR roles and table grids with confirmed PDF annotations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
IR = ROOT / "results" / "text-structure" / "ir"
GOLD = ROOT / "results" / "text-structure" / "manual-annotations"
SAMPLES = ["SELF-001", "SELF-002", "SELF-003"]


def norm(text: str) -> str:
    return " ".join((text or "").split()).casefold()


def iou(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b:
        return 0.0
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    aa = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    bb = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    return inter / (aa + bb - inter) if aa + bb - inter else 0.0


def expected(label: str) -> str:
    return {"title": "heading", "heading": "heading", "paragraph": "paragraph", "table": "table", "footnote": "footnote", "footer": "footer"}.get(label, label)


def score(sample: str) -> dict[str, Any]:
    ir = json.loads((IR / f"{sample}.docling.json").read_text(encoding="utf-8"))
    gold = json.loads((GOLD / f"{sample}.json").read_text(encoding="utf-8"))
    elements = ir["elements"]
    used: set[str] = set()
    results = []
    for unit in gold.get("units", []):
        candidates = [e for e in elements if e["element_id"] not in used and norm(e.get("text", "")) == norm(unit.get("text", ""))]
        if not candidates:
            candidates = [e for e in elements if e["element_id"] not in used and iou(e.get("bbox"), unit.get("bbox")) >= 0.5]
        candidate = max(candidates, key=lambda e: iou(e.get("bbox"), unit.get("bbox")), default=None)
        if candidate:
            used.add(candidate["element_id"])
        results.append((unit, candidate))
    role_matches = sum(pred is not None and pred["element_type"] == expected(unit["label"]) for unit, pred in results)
    footnotes = [(unit, pred) for unit, pred in results if unit["label"] == "footnote"]
    footnote_matches = sum(pred is not None and pred["element_type"] == "footnote" for _, pred in footnotes)
    footers = [(unit, pred) for unit, pred in results if unit["label"] == "footer"]
    footer_matches = sum(pred is not None and pred["element_type"] == "footer" for _, pred in footers)
    table_pred = [e for e in elements if e["element_type"] == "table"]
    table_gold = gold.get("table_grids", [])
    tables = [{
        "table_id": grid.get("table_id"),
        "gold_shape": [grid.get("rows"), grid.get("columns")],
        "predicted_shape": [table_pred[0].get("row_count"), table_pred[0].get("column_count")] if table_pred else None,
        "grid_shape_correct": bool(table_pred and [table_pred[0].get("row_count"), table_pred[0].get("column_count")] == [grid.get("rows"), grid.get("columns")]),
        "predicted_cell_count": sum(len(e.get("children_ids", [])) for e in table_pred),
        "cell_texts_available": sum(len(e.get("children_ids", [])) for e in table_pred) > 0,
    } for grid in table_gold]
    return {
        "experiment_id": "TECH-STRUCT-004-R01",
        "sample_id": sample,
        "parser": "Docling",
        "gold_units": len(results),
        "predicted_elements": len(elements),
        "matched_units": sum(pred is not None for _, pred in results),
        "bbox_coverage": sum(pred is not None for _, pred in results) / len(results) if results else None,
        "semantic_role_recall": role_matches / len(results) if results else None,
        "footnote_gold": len(footnotes),
        "footnote_semantic_matches": footnote_matches,
        "footer_gold": len(footers),
        "footer_semantic_matches": footer_matches,
        "tables": tables,
        "boundary": "Docling raw export mapped with OCR and formula enrichment disabled.",
    }


def main() -> None:
    report = {
        "experiment_id": "TECH-STRUCT-004-R01",
        "scope": "Docling semantic roles and table grid against confirmed text-PDF annotations",
        "outputs": [score(sample) for sample in SAMPLES],
        "boundary": "Three self-authored text PDFs only; no OCR or downstream QA claim.",
    }
    (IR / "docling-score.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
