"""Inspect DOCX OOXML layout signals without claiming visual pagination."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples" / "self-authored" / "docx"
FILES = {name: SAMPLES / filename for name, filename in {
    "SELF-005": "SELF-005-structured.docx",
    "SELF-006": "SELF-006-meeting-notes.docx",
    "SELF-007": "SELF-007-complex.docx",
}.items()}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(sample_id: str) -> dict:
    path = FILES[sample_id]
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        document = ET.fromstring(archive.read("word/document.xml"))
        paragraphs = document.findall(f".//{W}p")
        page_breaks = []
        section_count = 0
        for index, paragraph in enumerate(paragraphs, start=1):
            xml = ET.tostring(paragraph, encoding="unicode")
            has_page_break = any(
                node.tag == f"{W}br" and node.get(f"{W}type") == "page"
                for node in paragraph.iter()
            )
            if has_page_break or paragraph.find(f".//{W}lastRenderedPageBreak") is not None:
                page_breaks.append(index)
            if paragraph.find(f".//{W}sectPr") is not None:
                section_count += 1
        headers = sorted(name for name in names if name.startswith("word/header"))
        footers = sorted(name for name in names if name.startswith("word/footer"))
        footnotes = "word/footnotes.xml" in names
        endnotes = "word/endnotes.xml" in names
        comments = "word/comments.xml" in names
        explicit_break_paragraphs = []
        for index, paragraph in enumerate(paragraphs, start=1):
            text = "".join(node.text or "" for node in paragraph.iter(f"{W}t"))
            if text:
                explicit_break_paragraphs.append({"paragraph_index": index, "text_preview": text[:120]})
    return {
        "experiment_id": "TECH-STRUCT-006-R01",
        "sample_id": sample_id,
        "source_path": str(path.relative_to(ROOT)),
        "source_hash": sha256(path),
        "format": "DOCX",
        "paragraph_count_in_document_xml": len(paragraphs),
        "explicit_page_break_paragraph_indexes": page_breaks,
        "explicit_page_break_count": len(page_breaks),
        "section_count": section_count,
        "header_parts": headers,
        "footer_parts": footers,
        "has_footnotes_part": footnotes,
        "has_endnotes_part": endnotes,
        "has_comments_part": comments,
        "visual_page_numbers": "not_available_without_fixed_renderer",
        "boundary": "OOXML signals only; explicit breaks are not a complete visual pagination model.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="append", choices=sorted(FILES), dest="samples")
    args = parser.parse_args()
    outputs = [inspect(sample_id) for sample_id in (args.samples or list(FILES))]
    report = {"experiment_id": "TECH-STRUCT-006-R01", "outputs": outputs, "boundary": "No renderer available in this environment."}
    out = ROOT / "results" / "text-structure" / "docx-layout.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
