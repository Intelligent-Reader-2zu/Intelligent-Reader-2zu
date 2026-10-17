"""Build a conservative baseline IR for selected external PDF/HTML samples.

PDF headings are candidates only. HTML headings are DOM observations, not a
claim that all headings belong to the article body.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "results" / "text-structure" / "external-inventory.json"
OUT_DIR = ROOT / "results" / "text-structure" / "external-ir"
SELECTED = {"OPEN-003", "OPEN-010", "OPEN-011", "WEB-001", "WEB-002", "WEB-004"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def element_id(sample_id: str, ordinal: int) -> str:
    return f"{sample_id.lower()}-e{ordinal:05d}"


def pdf_ir(sample_id: str, path: Path, source_url: str | None) -> dict[str, Any]:
    import fitz

    elements: list[dict[str, Any]] = []
    ordinal = 0
    with fitz.open(path) as document:
        page_count = len(document)
        for page_number, page in enumerate(document, start=1):
            blocks = page.get_text("dict").get("blocks", [])
            sizes = [
                float(span.get("size", 0))
                for block in blocks
                if block.get("type") == 0
                for line in block.get("lines", [])
                for span in line.get("spans", [])
                if span.get("text", "").strip()
            ]
            median_size = statistics.median(sizes) if sizes else None
            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    spans = [span for span in line.get("spans", []) if span.get("text", "").strip()]
                    if not spans:
                        continue
                    text = "".join(span.get("text", "") for span in spans).strip()
                    if not text:
                        continue
                    ordinal += 1
                    max_size = max(float(span.get("size", 0)) for span in spans)
                    flags = [int(span.get("flags", 0)) for span in spans]
                    bold_candidate = any(flag & 16 for flag in flags)
                    short_candidate = len(text) <= 160 and text.count(" ") <= 18
                    size_candidate = bool(median_size and max_size >= median_size * 1.18)
                    candidate = bool(short_candidate and (bold_candidate or size_candidate))
                    elements.append(
                        {
                            "element_id": element_id(sample_id, ordinal),
                            "element_type": "heading_candidate" if candidate else "line",
                            "text": text,
                            "normalized_text": " ".join(text.split()).casefold(),
                            "physical_page": page_number,
                            "bbox": list(line.get("bbox", block.get("bbox", []))),
                            "reading_order_index": ordinal,
                            "heading_level": None,
                            "confidence": round(min(0.95, 0.45 + (0.2 if bold_candidate else 0) + (0.2 if size_candidate else 0)), 2) if candidate else None,
                            "warnings": [
                                "heuristic heading candidate; requires visual/manual confirmation"
                            ] if candidate else [],
                        }
                    )
    heading_candidates = [element for element in elements if element["element_type"] == "heading_candidate"]
    return {
        "sample_id": sample_id,
        "source_format": "PDF",
        "source_url": source_url,
        "source_path": str(path),
        "source_hash": sha256(path),
        "parser_name": "PyMuPDF conservative baseline",
        "parser_version": None,
        "config_hash": "pdf-line-candidate-v1",
        "elements": elements,
        "summary": {
            "element_count": len(elements),
            "heading_candidate_count": len(heading_candidates),
            "page_count": page_count,
            "bbox_completeness": sum(bool(e.get("bbox")) for e in elements) / len(elements) if elements else None,
            "physical_page_completeness": sum(e.get("physical_page") is not None for e in elements) / len(elements) if elements else None,
        },
        "boundary": "PDF lines and heuristic heading candidates only; no table, footnote, formula, reading-order, or gold-label accuracy claim.",
    }


def css_path(element: Any) -> str:
    parts = []
    current = element
    while current is not None and getattr(current, "name", None) not in {None, "[document]"}:
        name = current.name
        if current.get("id"):
            escaped_id = str(current["id"]).replace("\\", "\\\\").replace('"', '\\"')
            parts.append(f'{name}[id="{escaped_id}"]')
            break
        parent = current.parent
        siblings = parent.find_all(name, recursive=False) if parent else []
        index = siblings.index(current) + 1 if current in siblings else 1
        parts.append(f"{name}:nth-of-type({index})")
        current = parent
    return " > ".join(reversed(parts))


def html_ir(sample_id: str, path: Path, source_url: str | None) -> dict[str, Any]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    elements: list[dict[str, Any]] = []
    ordinal = 0
    for heading in soup.find_all([f"h{level}" for level in range(1, 7)]):
        ordinal += 1
        text = " ".join(heading.get_text(" ", strip=True).split())
        selector = css_path(heading)
        elements.append(
            {
                "element_id": element_id(sample_id, ordinal),
                "element_type": "heading",
                "text": text,
                "normalized_text": text.casefold(),
                "heading_level": int(heading.name[1:]),
                "heading_path": [],
                "source_selector": selector,
                "role": "navigation_candidate" if heading.find_parent("nav") else "dom_heading",
                "confidence": None,
                "warnings": ["DOM heading may belong to navigation or generated content"],
            }
        )
    article_scope = soup.find("article") or soup.find("main")
    scoped_headings = article_scope.find_all([f"h{level}" for level in range(1, 7)]) if article_scope else []
    for element in elements:
        element["in_article_or_main"] = any(css_path(heading) == element["source_selector"] for heading in scoped_headings)
    return {
        "sample_id": sample_id,
        "source_format": "HTML",
        "source_url": source_url,
        "source_path": str(path),
        "source_hash": sha256(path),
        "parser_name": "BeautifulSoup DOM conservative baseline",
        "parser_version": None,
        "config_hash": "html-heading-dom-v1",
        "elements": elements,
        "summary": {
            "element_count": len(elements),
            "dom_heading_count": len(elements),
            "article_or_main_heading_count": sum(bool(e["in_article_or_main"]) for e in elements),
            "unique_selector_count": len({e["source_selector"] for e in elements}),
            "selector_completeness": sum(bool(e.get("source_selector")) for e in elements) / len(elements) if elements else None,
        },
        "noise_counts": {
            "nav": len(soup.find_all("nav")),
            "script": len(soup.find_all("script")),
            "style": len(soup.find_all("style")),
        },
        "boundary": "DOM heading observations only; no article extraction, table semantics, citation accuracy, or gold-label claim.",
    }


def main() -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = []
    for sample in inventory["samples"]:
        if sample.get("sample_id") not in SELECTED or sample.get("status") != "ok":
            continue
        path = Path(sample["path"])
        result = pdf_ir(sample["sample_id"], path, sample.get("source_url")) if path.suffix.lower() == ".pdf" else html_ir(sample["sample_id"], path, sample.get("source_url"))
        output_path = OUT_DIR / f"{sample['sample_id']}.json"
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append({"sample_id": sample["sample_id"], "path": str(output_path), "summary": result["summary"]})
    report = {
        "experiment_id": "TECH-STRUCT-015-R01",
        "scope": "external PDF/HTML conservative baseline IR",
        "outputs": outputs,
        "boundary": "Candidates and DOM observations only; no gold labels or accuracy claim.",
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
