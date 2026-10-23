"""Run Docling PDF layout/table extraction with OCR explicitly disabled."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples" / "self-authored" / "pdf"
RESULTS = ROOT / "results" / "text-structure" / "docling"
FILES = {
    "SELF-001": SAMPLES / "SELF-001-single-column.pdf",
    "SELF-002": SAMPLES / "SELF-002-two-column.pdf",
    "SELF-003": SAMPLES / "SELF-003-table-formula.pdf",
}


def configure_ascii_runtime() -> dict[str, str]:
    shared_cache = Path("D:/docling-cache")
    runtime = shared_cache if shared_cache.exists() else ROOT / ".runtime" / "docling"
    paths = {
        "TMP": runtime / "tmp",
        "TEMP": runtime / "tmp",
        "APPDATA": runtime / "appdata",
        "LOCALAPPDATA": runtime / "localappdata",
        "XDG_CACHE_HOME": runtime,
        "HF_HOME": runtime / "hf",
    }
    for key, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(path)
    return {key: str(path) for key, path in paths.items()}


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


def run(sample_ids: list[str]) -> dict:
    environment_overrides = configure_ascii_runtime()
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    RESULTS.mkdir(parents=True, exist_ok=True)
    options = PdfPipelineOptions(
        do_ocr=False,
        do_table_structure=True,
        do_formula_enrichment=False,
        generate_page_images=False,
        generate_picture_images=False,
    )
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
    outputs = []
    for sample_id in sample_ids:
        path = FILES[sample_id]
        started = time.perf_counter()
        try:
            conversion = converter.convert(str(path))
            document = conversion.document
            exported = document.export_to_dict()
            raw_path = RESULTS / f"{sample_id}.docling.json"
            raw_path.write_text(json.dumps(exported, ensure_ascii=False, indent=2), encoding="utf-8")
            markdown = document.export_to_markdown()
            result = {
                "experiment_id": "TECH-DOC-007-R01-text-structure",
                "sample_id": sample_id,
                "status": "scored",
                "parser": "Docling",
                "parser_version": version("docling"),
                "ocr": {"enabled": False, "status": "explicitly_disabled"},
                "pipeline_options": {
                    "do_ocr": False,
                    "do_table_structure": True,
                    "do_formula_enrichment": False,
                },
                "page_count": len(exported.get("pages", {})),
                "text_element_count": len(exported.get("texts", [])),
                "table_count": len(exported.get("tables", [])),
                "picture_count": len(exported.get("pictures", [])),
                "text_preview": markdown[:1500],
                "raw_export_path": str(raw_path.relative_to(ROOT)),
                "raw_export_sha256": sha256(raw_path),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "source_path": str(path.relative_to(ROOT)),
                "source_sha256": sha256(path),
                "boundary": "Text-layer/layout/table experiment only; OCR quality is out of scope.",
            }
        except Exception as error:
            result = {
                "experiment_id": "TECH-DOC-007-R01-text-structure",
                "sample_id": sample_id,
                "status": "failed",
                "parser": "Docling",
                "parser_version": version("docling"),
                "ocr": {"enabled": False, "status": "explicitly_disabled"},
                "error_type": type(error).__name__,
                "error": str(error),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "source_path": str(path.relative_to(ROOT)),
                "source_sha256": sha256(path),
            }
        (RESULTS / f"{sample_id}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(result)
    summary = {
        "experiment_id": "TECH-DOC-007-R01-text-structure",
        "parser": "Docling",
        "parser_version": version("docling"),
        "date": time.strftime("%Y-%m-%d"),
        "python": sys.version,
        "ocr_enabled": False,
        "samples": sample_ids,
        "outputs": outputs,
        "environment_overrides": environment_overrides,
        "boundary": "No OCR, cloud service, vector retrieval, or QA evaluation.",
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="append", choices=sorted(FILES), dest="samples")
    args = parser.parse_args()
    run(args.samples or list(FILES))


if __name__ == "__main__":
    main()
