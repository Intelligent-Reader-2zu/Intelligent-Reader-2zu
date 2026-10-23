"""Capture PyMuPDF DICT/RAWDICT structures for the non-OCR PDF experiment."""

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
RESULTS = ROOT / "results" / "text-structure" / "pymupdf"
FILES = {
    "SELF-001": SAMPLES / "SELF-001-single-column.pdf",
    "SELF-002": SAMPLES / "SELF-002-two-column.pdf",
    "SELF-003": SAMPLES / "SELF-003-table-formula.pdf",
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


def run(sample_ids: list[str]) -> dict[str, Any]:
    import fitz

    RESULTS.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, Any]] = []
    for sample_id in sample_ids:
        path = FILES[sample_id]
        started = time.perf_counter()
        pages: list[dict[str, Any]] = []
        try:
            with fitz.open(path) as document:
                for page_number, page in enumerate(document, start=1):
                    structured = page.get_text("dict", sort=False)
                    raw = page.get_text("rawdict", sort=False)
                    pages.append(
                        {
                            "physical_page": page_number,
                            "rect": list(page.rect),
                            "dict": structured,
                            "rawdict": raw,
                        }
                    )
            result: dict[str, Any] = {
                "experiment_id": "TECH-DOC-007-R02-text-structure",
                "sample_id": sample_id,
                "format": "PDF",
                "status": "scored" if any(
                    block.get("lines") for page in pages for block in page["dict"].get("blocks", [])
                ) else "out_of_scope_no_text_layer",
                "parser": "PyMuPDF",
                "parser_version": version("PyMuPDF"),
                "ocr": {"enabled": False, "status": "not_run"},
                "config": {"dict_sort": False, "rawdict_sort": False, "include_images": True},
                "page_count": len(pages),
                "pages": pages,
                "source_path": str(path.relative_to(ROOT)),
                "source_sha256": sha256(path),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "boundary": "Text-layer structure only; OCR quality is out of scope.",
            }
        except Exception as error:
            result = {
                "experiment_id": "TECH-DOC-007-R02-text-structure",
                "sample_id": sample_id,
                "format": "PDF",
                "status": "failed",
                "parser": "PyMuPDF",
                "parser_version": version("PyMuPDF"),
                "ocr": {"enabled": False, "status": "not_run"},
                "error_type": type(error).__name__,
                "error": str(error),
                "source_path": str(path.relative_to(ROOT)),
                "source_sha256": sha256(path),
            }
        (RESULTS / f"{sample_id}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        outputs.append(result)
    summary = {
        "experiment_id": "TECH-DOC-007-R02-text-structure",
        "date": time.strftime("%Y-%m-%d"),
        "python": sys.version,
        "parser": "PyMuPDF",
        "parser_version": version("PyMuPDF"),
        "ocr_enabled": False,
        "samples": sample_ids,
        "outputs": outputs,
        "boundary": "No OCR, cloud service, vector retrieval, or QA evaluation.",
    }
    (RESULTS / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="append", choices=sorted(FILES), dest="samples")
    args = parser.parse_args()
    run(args.samples or list(FILES))


if __name__ == "__main__":
    main()
