"""Compare Docling section headers with PDF embedded TOC entries.

The PDF TOC is only a weak reference: it can omit visible headings or contain
entries that are not rendered as body headings. Results are therefore proxies,
not structure accuracy scores.
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDFS = {
    "OPEN-003": ROOT / "samples" / "external-candidates" / "nist-sp-800-63b.pdf",
    "OPEN-010": ROOT / "samples" / "external-candidates" / "docling-technical-report.pdf",
    "OPEN-011": ROOT / "samples" / "external-candidates" / "layoutlmv3.pdf",
}
DOC_OUT = ROOT / "results" / "text-structure" / "external-docling"
OUT = ROOT / "results" / "text-structure" / "external-docling-toc-overlap.json"


def compact(value: str) -> str:
    return "".join(char.casefold() for char in value if char.isalnum())


def similar(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, compact(left), compact(right)).ratio()


def best_match(value: str, candidates: list[str]) -> tuple[str | None, float]:
    if not candidates:
        return None, 0.0
    scored = [(candidate, similar(value, candidate)) for candidate in candidates]
    return max(scored, key=lambda pair: pair[1])


def score(sample_id: str, path: Path) -> dict[str, Any]:
    raw = json.loads((DOC_OUT / f"{sample_id}.docling.json").read_text(encoding="utf-8"))
    headers = [item.get("text", "") for item in raw.get("texts", []) if item.get("label") == "section_header"]
    with fitz.open(path) as document:
        toc = document.get_toc(simple=True)
    toc_titles = [row[1] for row in toc if len(row) > 1 and row[1]]
    header_matches = [best_match(title, headers) for title in toc_titles]
    reverse_matches = [best_match(title, toc_titles) for title in headers]
    threshold = 0.86
    toc_matched = [match for match in header_matches if match[1] >= threshold]
    header_matched = [match for match in reverse_matches if match[1] >= threshold]
    return {
        "sample_id": sample_id,
        "toc_entry_count": len(toc_titles),
        "docling_section_header_count": len(headers),
        "matching_threshold": threshold,
        "toc_to_docling_overlap_proxy": len(toc_matched) / len(toc_titles) if toc_titles else None,
        "docling_to_toc_overlap_proxy": len(header_matched) / len(headers) if headers else None,
        "toc_level_distribution": {
            str(level): sum(1 for row in toc if row and row[0] == level)
            for level in sorted({row[0] for row in toc if row})
        },
        "docling_level_distribution": {
            str(level): sum(1 for item in raw.get("texts", []) if item.get("label") == "section_header" and item.get("level") == level)
            for level in sorted({item.get("level") for item in raw.get("texts", []) if item.get("label") == "section_header"})
        },
        "toc_unmatched_preview": [
            {"toc_title": title, "best_docling": match[0], "similarity": round(match[1], 3)}
            for title, match in zip(toc_titles, header_matches)
            if match[1] < threshold
        ][:20],
        "docling_unmatched_preview": [
            {"docling_header": title, "best_toc": match[0], "similarity": round(match[1], 3)}
            for title, match in zip(headers, reverse_matches)
            if match[1] < threshold
        ][:20],
        "boundary": "Embedded TOC is a weak reference, not a gold annotation or accuracy label.",
    }


def main() -> None:
    results = [score(sample_id, path) for sample_id, path in PDFS.items()]
    report = {
        "experiment_id": "TECH-STRUCT-017-R01",
        "scope": "Docling section-header versus embedded PDF TOC overlap proxy",
        "results": results,
        "boundary": "TOC overlap proxy only; no gold labels, reading-order, table, formula, citation, retrieval, or QA accuracy claim.",
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
