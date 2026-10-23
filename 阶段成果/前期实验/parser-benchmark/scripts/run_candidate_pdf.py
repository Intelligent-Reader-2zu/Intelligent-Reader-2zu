"""Run pdfplumber, Docling and Unstructured against authored PDF fixtures.

The output is intentionally a compact experiment record. Raw vendor output is
not silently converted to a product IR; this script records enough metadata to
locate the original sample and compare candidate behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples" / "self-authored" / "pdf"
RESULTS = ROOT / "results" / "candidate-pdf"
FILES = {
    "SELF-001": SAMPLES / "SELF-001-single-column.pdf",
    "SELF-002": SAMPLES / "SELF-002-two-column.pdf",
    "SELF-003": SAMPLES / "SELF-003-table-formula.pdf",
    "SELF-004": SAMPLES / "SELF-004-scanned.pdf",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def pdfplumber_result(sample_id: str, path: Path) -> dict[str, Any]:
    import pdfplumber

    started = time.perf_counter()
    pages = []
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            words = page.extract_words() or []
            rects = len(page.rects)
            lines = len(page.lines)
            images = len(page.images)
            tables = page.find_tables()
            pages.append(
                {
                    "physical_page": number,
                    "text_chars": len(text),
                    "word_count": len(words),
                    "rect_count": rects,
                    "line_count": lines,
                    "image_count": images,
                    "table_candidate_count": len(tables),
                    "bbox_sample": (
                        [words[0][key] for key in ("x0", "top", "x1", "bottom")]
                        if words else None
                    ),
                }
            )
            text_parts.append(text)
    text = "\n".join(text_parts)
    return {
        "parser": "pdfplumber",
        "parser_version": version("pdfplumber"),
        "status": "succeeded",
        "sample_id": sample_id,
        "page_count": len(pages),
        "text_chars": len(text),
        "text_layer_present": bool(text.strip()),
        "pages": pages,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "text_preview": text[:1500],
        "ocr_status": "not_run",
    }


def docling_result(sample_id: str, path: Path) -> dict[str, Any]:
    from docling.document_converter import DocumentConverter

    started = time.perf_counter()
    converter = DocumentConverter()
    conversion = converter.convert(str(path))
    document = conversion.document
    markdown = document.export_to_markdown()
    exported = document.export_to_dict()
    raw_path = RESULTS / f"{sample_id}.docling.json"
    raw_path.write_text(json.dumps(exported, ensure_ascii=False, indent=2), encoding="utf-8")
    pages = exported.get("pages", {}) if isinstance(exported, dict) else {}
    texts = exported.get("texts", []) if isinstance(exported, dict) else []
    pictures = exported.get("pictures", []) if isinstance(exported, dict) else []
    tables = exported.get("tables", []) if isinstance(exported, dict) else []
    return {
        "parser": "Docling",
        "parser_version": version("docling"),
        "status": "succeeded",
        "sample_id": sample_id,
        "page_count_from_export": len(pages) if isinstance(pages, dict) else None,
        "text_element_count": len(texts) if isinstance(texts, list) else None,
        "picture_count": len(pictures) if isinstance(pictures, list) else None,
        "table_count": len(tables) if isinstance(tables, list) else None,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "text_preview": markdown[:1500],
        "raw_export_keys": list(exported.keys()) if isinstance(exported, dict) else [],
        "raw_export_path": str(raw_path.relative_to(ROOT)),
        "raw_export_sha256": sha256(raw_path),
        "ocr_status": "observed_text_on_scanned_sample; config_not_explicitly_overridden",
    }


def unstructured_result(sample_id: str, path: Path, strategy: str, languages: str) -> dict[str, Any]:
    from unstructured.partition.pdf import partition_pdf

    started = time.perf_counter()
    elements = partition_pdf(
        filename=str(path),
        strategy=strategy,
        include_page_breaks=True,
        languages=languages.split("+") if languages else None,
    )
    serialized = [element.to_dict() for element in elements]
    raw_path = RESULTS / f"{sample_id}.unstructured-{strategy}.json"
    raw_path.write_text(json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8")
    text = "\n".join(element.get("text", "") for element in serialized)
    types: dict[str, int] = {}
    pages: set[int] = set()
    for element in serialized:
        types[element.get("type", "unknown")] = types.get(element.get("type", "unknown"), 0) + 1
        page_number = element.get("metadata", {}).get("page_number")
        if isinstance(page_number, int):
            pages.add(page_number)
    return {
        "parser": "Unstructured",
        "parser_version": version("unstructured"),
        "status": "succeeded",
        "sample_id": sample_id,
        "strategy": strategy,
        "ocr_languages": languages.split("+") if languages else None,
        "element_count": len(serialized),
        "element_types": types,
        "physical_pages_observed": sorted(pages),
        "text_chars": len(text),
        "text_layer_present": bool(text.strip()),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "text_preview": text[:1500],
        "raw_element_path": str(raw_path.relative_to(ROOT)),
        "raw_element_sha256": sha256(raw_path),
        "ocr_status": "not_run" if strategy == "fast" else "strategy_may_use_ocr; verify output and configuration",
    }


def run(parser_name: str, sample_ids: list[str], strategy: str, languages: str) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    all_results = []
    for sample_id in sample_ids:
        path = FILES[sample_id]
        try:
            if parser_name == "pdfplumber":
                result = pdfplumber_result(sample_id, path)
            elif parser_name == "docling":
                result = docling_result(sample_id, path)
            else:
                result = unstructured_result(sample_id, path, strategy, languages)
            result["source_path"] = str(path.relative_to(ROOT))
            result["source_sha256"] = sha256(path)
        except Exception as error:
            result = {
                "parser": parser_name,
                "parser_version": version(parser_name if parser_name != "docling" else "docling"),
                "status": "failed",
                "sample_id": sample_id,
                "source_path": str(path.relative_to(ROOT)),
                "source_sha256": sha256(path),
                "error_type": type(error).__name__,
                "error": str(error),
            }
        suffix = f"-{strategy}" if parser_name == "unstructured" else ""
        (RESULTS / f"{parser_name}{suffix}-{sample_id}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        all_results.append(result)
    summary = {
        "experiment_id": f"TECH-DOC-candidate-{parser_name}-{strategy if parser_name == 'unstructured' else 'default'}",
        "date": time.strftime("%Y-%m-%d"),
        "python": sys.version,
        "parser": parser_name,
        "strategy": strategy if parser_name == "unstructured" else None,
        "ocr_languages": languages.split("+") if parser_name == "unstructured" else None,
        "samples": sample_ids,
        "results": all_results,
        "boundary": "Candidate smoke test only; not a quality acceptance result.",
    }
    summary_suffix = f"-{strategy}" if parser_name == "unstructured" else ""
    (RESULTS / f"{parser_name}{summary_suffix}-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parser", choices=["pdfplumber", "docling", "unstructured"], required=True)
    parser.add_argument("--strategy", choices=["fast", "hi_res", "ocr_only"], default="fast")
    parser.add_argument("--languages", default="eng", help="Unstructured OCR language codes joined by +")
    parser.add_argument("--sample", action="append", choices=sorted(FILES), dest="samples")
    args = parser.parse_args()
    run(args.parser, args.samples or list(FILES), args.strategy, args.languages)


if __name__ == "__main__":
    main()
