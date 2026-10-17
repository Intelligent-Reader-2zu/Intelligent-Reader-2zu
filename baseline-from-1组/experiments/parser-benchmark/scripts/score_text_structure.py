"""Score automatic, evidence-based checks and report manual annotation gaps."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples" / "self-authored"
RESULTS = ROOT / "results" / "text-structure"
ANNOTATIONS = SAMPLES / "annotations"
SAMPLE_IDS = ["SELF-001", "SELF-002", "SELF-003"]
FIXTURE_STATUS = {
    "SELF-001": "usable_for_basic_text_structure",
    "SELF-002": "usable_regenerated_two_column_fixture",
    "SELF-003": "usable_for_basic_table_and_formula_presence_only",
}
PARSERS = {
    "pymupdf": RESULTS / "pymupdf",
    "baseline": RESULTS,
    "docling": RESULTS / "docling",
    "tika": RESULTS / "tika",
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def result_text(result: dict[str, Any]) -> str:
    if "text_preview" in result:
        return str(result["text_preview"])
    parts: list[str] = []
    for page in result.get("pages", []):
        for block in page.get("dict", {}).get("blocks", []):
            for line in block.get("lines", []):
                parts.append("".join(span.get("text", "") for span in line.get("spans", [])))
    return "\n".join(parts)


def count_pymupdf(result: dict[str, Any]) -> dict[str, int]:
    blocks = lines = spans = chars = 0
    for page in result.get("pages", []):
        for block in page.get("dict", {}).get("blocks", []):
            if "lines" not in block:
                continue
            blocks += 1
            for line in block["lines"]:
                lines += 1
                for span in line.get("spans", []):
                    spans += 1
                    chars += len(span.get("text", ""))
    return {"text_blocks": blocks, "lines": lines, "spans": spans, "span_chars": chars}


def load_annotation(sample_id: str) -> dict[str, Any]:
    return json.loads((ANNOTATIONS / f"{sample_id}.json").read_text(encoding="utf-8"))


def load_result(directory: Path, sample_id: str) -> dict[str, Any] | None:
    path = directory / f"{sample_id}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def score_one(parser_name: str, directory: Path, sample_id: str) -> dict[str, Any]:
    result = load_result(directory, sample_id)
    annotation = load_annotation(sample_id)
    if result is None:
        return {"status": "missing_result", "parser": parser_name, "sample_id": sample_id}
    text = normalize(result_text(result))
    fragments = annotation.get("expected_evidence_fragments", [])
    queries = annotation.get("fixed_queries", [])
    fragment_hits = {fragment: normalize(fragment) in text for fragment in fragments}
    query_hits = {query: normalize(query) in text for query in queries}
    bbox_count = 0
    if parser_name == "pymupdf":
        for page in result.get("pages", []):
            for block in page.get("dict", {}).get("blocks", []):
                if "lines" in block and block.get("bbox"):
                    bbox_count += 1
    return {
        "experiment_id": "TECH-DOC-007-R02-text-structure",
        "parser": parser_name,
        "sample_id": sample_id,
        "fixture_status": FIXTURE_STATUS[sample_id],
        "status": result.get("status"),
        "page_count": result.get("page_count"),
        "text_chars": len(text),
        "fragment_recall": sum(fragment_hits.values()) / len(fragment_hits) if fragment_hits else None,
        "fragment_hits": fragment_hits,
        "query_recall": sum(query_hits.values()) / len(query_hits) if query_hits else None,
        "query_hits": query_hits,
        "bbox_text_block_count": bbox_count,
        "manual_required": [
            "reading_order_sequence",
            "paragraph_boundaries",
            "heading_level_and_path",
            "table_cell_grid_and_spans",
            "header_footer_classification",
        ],
        "excluded_metrics": [],
        "boundary": "Automatic fragment/query checks are not a substitute for human structural gold labels.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="append", choices=SAMPLE_IDS, dest="samples")
    args = parser.parse_args()
    samples = args.samples or SAMPLE_IDS
    outputs = [score_one(name, directory, sample_id) for name, directory in PARSERS.items() for sample_id in samples]
    report = {
        "experiment_id": "TECH-DOC-007-R02-text-structure",
        "scope": "non-OCR text/layout evidence checks",
        "outputs": outputs,
        "manual_annotation_status": "required_for_reading_order_paragraph_heading_table_metrics",
    }
    out = RESULTS / "automatic-score.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
