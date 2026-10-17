"""Inventory downloaded external samples without changing parser predictions.

This is a manifest-driven smoke inventory. It verifies file hashes and records
cheap structural signals for PDF and HTML samples. It does not claim license
approval, gold-label correctness, or product-level parsing accuracy.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = [
    ROOT / "samples" / "external-candidates" / "external-candidate-manifest.json",
    ROOT / "samples" / "external-replacements" / "external-replacement-manifest.json",
    ROOT / "samples" / "open-authored-substitutes" / "auth-substitute-manifest.json",
]
OUT = ROOT / "results" / "text-structure" / "external-inventory.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pdf_signals(path: Path) -> dict[str, Any]:
    import fitz

    with fitz.open(path) as document:
        page_stats = []
        text_chars = 0
        image_count = 0
        for page in document:
            text = page.get_text("text") or ""
            text_chars += len(text)
            image_count += len(page.get_images(full=True))
            page_stats.append({"text_chars": len(text), "block_count": len(page.get_text("blocks"))})
        toc = document.get_toc(simple=True)
        return {
            "page_count": len(document),
            "text_chars": text_chars,
            "image_count": image_count,
            "toc_entry_count": len(toc),
            "toc_max_level": max((row[0] for row in toc), default=None),
            "page_stats_sample": page_stats[:3],
            "text_layer_present": text_chars > 0,
        }


def html_signals(path: Path) -> dict[str, Any]:
    from bs4 import BeautifulSoup

    raw = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    headings = soup.find_all(re.compile(r"^h[1-6]$"))
    return {
        "text_chars": len(soup.get_text(" ", strip=True)),
        "heading_count": len(headings),
        "heading_levels": {str(level): len(soup.find_all(f"h{level}")) for level in range(1, 7)},
        "table_count": len(soup.find_all("table")),
        "pre_or_code_count": len(soup.find_all(["pre", "code"])),
        "link_count": len(soup.find_all("a")),
        "nav_count": len(soup.find_all("nav")),
        "script_count": len(soup.find_all("script")),
        "style_count": len(soup.find_all("style")),
    }


def inspect_sample(entry: dict[str, Any]) -> dict[str, Any]:
    path = Path(entry["path"])
    result: dict[str, Any] = {
        "sample_id": entry.get("sample_id"),
        "filename": entry.get("filename"),
        "source_url": entry.get("source_url"),
        "retrieved_on": entry.get("retrieved_on"),
        "format": entry.get("format"),
        "license_or_authorization": entry.get("license_or_authorization"),
        "cloud_upload_allowed": entry.get("cloud_upload_allowed"),
        "expected_layout_features": entry.get("expected_layout_features", []),
        "path": str(path),
        "exists": path.exists(),
    }
    if not path.exists():
        result["status"] = "missing"
        return result
    actual_hash = sha256(path)
    result.update(
        {
            "status": "ok" if actual_hash == entry.get("sha256") else "hash_mismatch",
            "bytes": path.stat().st_size,
            "manifest_sha256": entry.get("sha256"),
            "actual_sha256": actual_hash,
        }
    )
    try:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            result["signals"] = pdf_signals(path)
        elif suffix in {".html", ".htm"}:
            result["signals"] = html_signals(path)
        else:
            result["signals"] = {"unsupported_suffix": suffix}
    except Exception as error:  # keep the inventory useful when one file is malformed
        result["status"] = "inspection_failed"
        result["error_type"] = type(error).__name__
        result["error"] = str(error)
    return result


def main() -> None:
    entries: list[dict[str, Any]] = []
    for manifest_path in MANIFESTS:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest.get("samples", []):
            inspected = inspect_sample(entry)
            inspected["manifest"] = str(manifest_path.relative_to(ROOT))
            entries.append(inspected)
    summary = {
        "experiment_id": "TECH-STRUCT-011-R01",
        "scope": "downloaded external sample hash and cheap structure inventory",
        "manifests": [str(path.relative_to(ROOT)) for path in MANIFESTS],
        "sample_count": len(entries),
        "status_counts": {
            status: sum(item.get("status") == status for item in entries)
            for status in sorted({item.get("status") for item in entries})
        },
        "samples": entries,
        "boundary": "Inventory only; no license approval, gold labels, parser accuracy, OCR, retrieval, or QA evaluation.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
