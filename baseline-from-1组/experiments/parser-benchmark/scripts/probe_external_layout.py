"""Probe representative external samples for layout-risk stratification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "results" / "text-structure" / "external-inventory.json"
OUT = ROOT / "results" / "text-structure" / "external-layout-probe.json"
SELECTED = {"OPEN-003", "OPEN-010", "OPEN-011", "WEB-001", "WEB-002", "WEB-004"}


def pdf_probe(path: Path) -> dict[str, Any]:
    import fitz

    with fitz.open(path) as document:
        multi_column_pages = []
        for page_number, page in enumerate(document, start=1):
            words = page.get_text("words")
            if not words:
                continue
            width = page.rect.width or 1
            x_positions = sorted({round(float(word[0]), 1) for word in words})
            clusters: list[list[float]] = []
            for x_position in x_positions:
                if not clusters or x_position - clusters[-1][-1] > width * 0.12:
                    clusters.append([x_position])
                else:
                    clusters[-1].append(x_position)
            if len(clusters) >= 2:
                multi_column_pages.append({"page": page_number, "x_cluster_count": len(clusters)})
        toc = document.get_toc(simple=True)
        return {
            "kind": "PDF",
            "page_count": len(document),
            "toc_entry_count": len(toc),
            "toc_preview": toc[:12],
            "suspected_multi_column_page_count": len(multi_column_pages),
            "suspected_multi_column_page_ratio": len(multi_column_pages) / len(document) if document else None,
            "multi_column_pages_preview": multi_column_pages[:12],
            "heuristic_warning": "x-coordinate clusters are a layout-risk signal, not a reading-order label",
        }


def html_probe(path: Path) -> dict[str, Any]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    headings = []
    for heading in soup.find_all([f"h{level}" for level in range(1, 7)]):
        level = int(heading.name[1:])
        headings.append({"level": level, "text": " ".join(heading.get_text(" ", strip=True).split())[:160], "id": heading.get("id")})
    ids = [heading["id"] for heading in headings if heading["id"]]
    return {
        "kind": "HTML",
        "heading_count": len(headings),
        "heading_preview": headings[:20],
        "heading_id_count": len(ids),
        "unique_heading_id_ratio": len(set(ids)) / len(ids) if ids else None,
        "table_count": len(soup.find_all("table")),
        "code_block_count": len(soup.find_all(["pre", "code"])),
        "anchor_count": len(soup.find_all("a")),
        "nav_count": len(soup.find_all("nav")),
        "article_count": len(soup.find_all("article")),
        "script_count": len(soup.find_all("script")),
        "style_count": len(soup.find_all("style")),
        "heuristic_warning": "DOM heading counts include navigation or generated content until article extraction is applied",
    }


def main() -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    probes = []
    for sample in inventory["samples"]:
        if sample.get("sample_id") not in SELECTED or sample.get("status") != "ok":
            continue
        path = Path(sample["path"])
        result = {"sample_id": sample["sample_id"], "source_url": sample.get("source_url"), "path": str(path)}
        result["probe"] = pdf_probe(path) if path.suffix.lower() == ".pdf" else html_probe(path)
        probes.append(result)
    report = {
        "experiment_id": "TECH-STRUCT-012-R01",
        "scope": "representative external PDF/HTML layout-risk probe",
        "selected_sample_ids": sorted(SELECTED),
        "probes": probes,
        "boundary": "Heuristic signals only; no gold labels, reading-order accuracy, title F1, license approval, retrieval, or QA evaluation.",
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
