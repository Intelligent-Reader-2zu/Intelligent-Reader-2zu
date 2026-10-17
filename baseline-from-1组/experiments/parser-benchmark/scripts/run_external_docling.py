"""Run the existing isolated Docling environment on external PDF samples."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples" / "external-candidates"
RESULTS = ROOT / "results" / "text-structure" / "external-docling"
FILES = {
    "OPEN-003": SAMPLES / "nist-sp-800-63b.pdf",
    "OPEN-010": SAMPLES / "docling-technical-report.pdf",
    "OPEN-011": SAMPLES / "layoutlmv3.pdf",
}


def configure_ascii_cache() -> dict[str, str]:
    runtime = Path("D:/docling-cache")
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
    os.environ["PYTHONUTF8"] = "1"
    return {key: str(path) for key, path in paths.items()}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def inspect_export(exported: dict[str, Any]) -> dict[str, Any]:
    texts = exported.get("texts", [])
    tables = exported.get("tables", [])
    pictures = exported.get("pictures", [])
    pages = exported.get("pages", {})
    labels: dict[str, int] = {}
    section_headers = []
    for item in texts if isinstance(texts, list) else []:
        label = str(item.get("label", "unknown"))
        labels[label] = labels.get(label, 0) + 1
        if label == "section_header":
            section_headers.append({
                "text": item.get("text", ""),
                "level": item.get("level"),
                "page_no": (item.get("prov") or [{}])[0].get("page_no"),
                "bbox": (item.get("prov") or [{}])[0].get("bbox"),
            })
    table_cells = 0
    for table in tables if isinstance(tables, list) else []:
        data = table.get("data", {}) if isinstance(table, dict) else {}
        table_cells += len(data.get("table_cells", [])) if isinstance(data, dict) else 0
    return {
        "page_count": len(pages) if isinstance(pages, dict) else None,
        "text_count": len(texts) if isinstance(texts, list) else None,
        "table_count": len(tables) if isinstance(tables, list) else None,
        "table_cell_count": table_cells,
        "picture_count": len(pictures) if isinstance(pictures, list) else None,
        "text_labels": labels,
        "section_header_count": len(section_headers),
        "section_header_preview": section_headers[:30],
    }


def run(sample_ids: list[str]) -> dict[str, Any]:
    cache = configure_ascii_cache()
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
        raw_path = RESULTS / f"{sample_id}.docling.json"
        try:
            conversion = converter.convert(str(path))
            document = conversion.document
            exported = document.export_to_dict()
            raw_path.write_text(json.dumps(exported, ensure_ascii=False, indent=2), encoding="utf-8")
            result = {
                "experiment_id": "TECH-STRUCT-016-R01",
                "sample_id": sample_id,
                "status": "succeeded",
                "parser": "Docling",
                "parser_version": package_version("docling"),
                "source_path": str(path.relative_to(ROOT)),
                "source_sha256": sha256(path),
                "ocr": {"enabled": False, "status": "explicitly_disabled"},
                "pipeline_options": {
                    "do_ocr": False,
                    "do_table_structure": True,
                    "do_formula_enrichment": False,
                    "generate_page_images": False,
                    "generate_picture_images": False,
                },
                "raw_export_path": str(raw_path.relative_to(ROOT)),
                "raw_export_sha256": sha256(raw_path),
                "metrics": inspect_export(exported),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "boundary": "External text-layer PDF smoke test; no gold labels, OCR, reading-order, or QA accuracy claim.",
            }
        except Exception as error:
            result = {
                "experiment_id": "TECH-STRUCT-016-R01",
                "sample_id": sample_id,
                "status": "failed",
                "parser": "Docling",
                "parser_version": package_version("docling"),
                "source_path": str(path.relative_to(ROOT)),
                "source_sha256": sha256(path),
                "error_type": type(error).__name__,
                "error": str(error),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        (RESULTS / f"{sample_id}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(result)
    summary = {
        "experiment_id": "TECH-STRUCT-016-R01",
        "parser": "Docling",
        "parser_version": package_version("docling"),
        "python": sys.version,
        "samples": sample_ids,
        "cache_environment": cache,
        "outputs": outputs,
        "boundary": "External text-layer PDF smoke test; no gold labels, OCR, reading-order, or QA accuracy claim.",
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="append", choices=sorted(FILES), dest="samples")
    args = parser.parse_args()
    run(args.samples or list(FILES))


if __name__ == "__main__":
    main()
