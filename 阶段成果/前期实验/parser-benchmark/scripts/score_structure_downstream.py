"""Check whether IR hits retain navigation and source-location evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
IR = ROOT / "results" / "text-structure" / "ir"
ANNOTATIONS = ROOT / "samples" / "self-authored" / "annotations"


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().casefold()


def location(element: dict[str, Any]) -> dict[str, Any] | None:
    if element.get("physical_page") is not None and element.get("bbox"):
        return {"kind": "pdf_page_bbox", "physical_page": element["physical_page"], "bbox": element["bbox"]}
    if element.get("source_line_start") is not None:
        return {"kind": "source_line", "start": element["source_line_start"], "end": element.get("source_line_end")}
    if element.get("source_selector"):
        return {"kind": "html_selector", "selector": element["source_selector"]}
    return None


def score_document(path: Path, annotation_path: Path | None, mode: str) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    annotations = json.loads(annotation_path.read_text(encoding="utf-8")) if annotation_path and annotation_path.exists() else {}
    queries = annotations.get("fixed_queries", [])
    fragments = annotations.get("expected_evidence_fragments", [])
    elements = document.get("elements", [])
    hits = []
    for query in queries + fragments:
        matches = [element for element in elements if norm(query) in norm(element.get("text", ""))]
        best = matches[0] if matches else None
        hits.append({
            "query": query,
            "matched": best is not None,
            "element_id": best.get("element_id") if best else None,
            "element_type": best.get("element_type") if best else None,
            "heading_path": best.get("heading_path") if best else None,
            "location": location(best) if best else None,
            "is_table_or_equation": best.get("element_type") in {"table", "table_cell", "equation"} if best else False,
        })
    matched = [item for item in hits if item["matched"]]
    with_heading = [item for item in matched if item["heading_path"]]
    with_location = [item for item in matched if item["location"]]
    return {
        "sample_id": document.get("sample_id"),
        "format": document.get("source_format"),
        "parser": document.get("parser_name"),
        "mode": mode,
        "query_count": len(hits),
        "query_recall": len(matched) / len(hits) if hits else None,
        "heading_path_retention": len(with_heading) / len(matched) if matched else None,
        "location_retention": len(with_location) / len(matched) if matched else None,
        "hits": hits,
        "boundary": "Fixed keyword/evidence checks only; not semantic retrieval or answer correctness.",
    }


def main() -> None:
    jobs = [
        (IR / "SELF-001.docling.json", ANNOTATIONS / "SELF-001.json", "docling-pdf"),
        (IR / "SELF-002.docling.json", ANNOTATIONS / "SELF-002.json", "docling-pdf"),
        (IR / "SELF-003.docling.json", ANNOTATIONS / "SELF-003.json", "docling-pdf"),
        (IR / "SELF-008.markdown-extended.json", ANNOTATIONS / "SELF-008.json", "markdown-extended"),
        (IR / "SELF-012.html.json", ANNOTATIONS / "SELF-012.json", "html-dom"),
    ]
    outputs = []
    for path, annotation, mode in jobs:
        if path.exists():
            outputs.append(score_document(path, annotation, mode))
    report = {
        "experiment_id": "TECH-STRUCT-008-R01",
        "scope": "navigation path and source-location retention after fixed evidence lookup",
        "outputs": outputs,
        "boundary": "No vector retrieval, QA model, or user click instrumentation.",
    }
    out = IR / "downstream-score.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
