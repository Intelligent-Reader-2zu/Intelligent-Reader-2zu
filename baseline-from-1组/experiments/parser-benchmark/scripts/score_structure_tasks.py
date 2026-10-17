"""Score product-facing structure tasks on the experimental IR outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
IR = ROOT / "results" / "text-structure" / "ir"
ANNOTATIONS = ROOT / "samples" / "self-authored" / "annotations"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def norm(text: str) -> str:
    return " ".join((text or "").split()).casefold()


def location(element: dict[str, Any]) -> bool:
    return bool(
        (element.get("physical_page") is not None and element.get("bbox"))
        or element.get("source_line_start") is not None
        or element.get("source_selector")
    )


def toc_score(document: dict[str, Any]) -> dict[str, Any]:
    headings = [e for e in document.get("elements", []) if e.get("element_type") == "heading"]
    ids = [e.get("element_id") for e in headings]
    unique_ids = len(ids) == len(set(ids))
    paths = [" > ".join(e.get("heading_path") or []) for e in headings]
    non_empty_paths = sum(bool(path) for path in paths)
    parent_ids = {e.get("element_id") for e in headings}
    valid_parents = sum(not e.get("parent_element_id") or e.get("parent_element_id") in parent_ids for e in headings)
    return {
        "heading_count": len(headings),
        "unique_heading_ids": unique_ids,
        "non_empty_heading_paths": non_empty_paths / len(headings) if headings else None,
        "valid_heading_parents": valid_parents / len(headings) if headings else None,
        "toc_ready": bool(headings and unique_ids and non_empty_paths == len(headings) and valid_parents == len(headings)),
    }


def evidence_score(document: dict[str, Any], annotation: dict[str, Any]) -> dict[str, Any]:
    elements = document.get("elements", [])
    queries = annotation.get("fixed_queries", []) + annotation.get("expected_evidence_fragments", [])
    hits = []
    for query in queries:
        matches = [e for e in elements if norm(query) in norm(e.get("text", ""))]
        best = matches[0] if matches else None
        hits.append({
            "query": query,
            "matched": best is not None,
            "element_id": best.get("element_id") if best else None,
            "heading_path": best.get("heading_path") if best else None,
            "location": location(best) if best else False,
            "element_type": best.get("element_type") if best else None,
        })
    matched = [h for h in hits if h["matched"]]
    return {
        "query_count": len(hits),
        "query_recall": len(matched) / len(hits) if hits else None,
        "heading_path_retention": sum(bool(h["heading_path"]) for h in matched) / len(matched) if matched else None,
        "location_retention": sum(h["location"] for h in matched) / len(matched) if matched else None,
        "hits": hits,
    }


def selector_score(document: dict[str, Any]) -> dict[str, Any]:
    located = [e for e in document.get("elements", []) if e.get("source_selector")]
    selectors = [e["source_selector"] for e in located]
    return {
        "selector_count": len(selectors),
        "unique_selector_count": len(set(selectors)),
        "selector_uniqueness": len(set(selectors)) / len(selectors) if selectors else None,
        "selector_ready": bool(selectors) and len(set(selectors)) == len(selectors),
    }


def main() -> None:
    jobs = [
        (IR / "SELF-001.docling.json", ANNOTATIONS / "SELF-001.json"),
        (IR / "SELF-002.docling.json", ANNOTATIONS / "SELF-002.json"),
        (IR / "SELF-003.docling.json", ANNOTATIONS / "SELF-003.json"),
        (IR / "SELF-008.markdown-extended.json", ANNOTATIONS / "SELF-008.json"),
        (IR / "SELF-012.html.json", ANNOTATIONS / "SELF-012.json"),
    ]
    outputs = []
    for path, annotation_path in jobs:
        if not path.exists():
            continue
        document = load(path)
        annotation = load(annotation_path)
        output = {
            "sample_id": document.get("sample_id"),
            "format": document.get("source_format"),
            "parser": document.get("parser_name"),
            "toc": toc_score(document),
            "evidence": evidence_score(document, annotation),
        }
        if document.get("source_format") == "HTML":
            output["selector"] = selector_score(document)
        outputs.append(output)
    report = {
        "experiment_id": "TECH-STRUCT-010-R01",
        "scope": "TOC/navigation, fixed evidence lookup, and location readiness",
        "outputs": outputs,
        "boundary": "Synthetic fixed queries and IR checks only; no UI click automation or semantic QA evaluation.",
    }
    out = IR / "task-score.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
