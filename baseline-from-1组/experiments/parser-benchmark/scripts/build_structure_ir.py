"""Map local parser outputs to a small, explicit structure IR.

This is an experiment adapter, not the production document model. Missing
location fields remain null so that format differences are visible in scores.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples" / "self-authored"
RESULTS = ROOT / "results" / "text-structure" / "ir"

FILES = {
    "SELF-001": SAMPLES / "pdf" / "SELF-001-single-column.pdf",
    "SELF-002": SAMPLES / "pdf" / "SELF-002-two-column.pdf",
    "SELF-003": SAMPLES / "pdf" / "SELF-003-table-formula.pdf",
    "SELF-005": SAMPLES / "docx" / "SELF-005-structured.docx",
    "SELF-006": SAMPLES / "docx" / "SELF-006-meeting-notes.docx",
    "SELF-007": SAMPLES / "docx" / "SELF-007-complex.docx",
    "SELF-008": SAMPLES / "markdown" / "SELF-008-complex.md",
    "SELF-009": SAMPLES / "markdown" / "SELF-009-heading-levels.md",
    "SELF-010": SAMPLES / "txt" / "SELF-010-utf8.txt",
    "SELF-011": SAMPLES / "txt" / "SELF-011-gb18030.txt",
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


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def config_hash(config: dict[str, Any]) -> str:
    raw = json.dumps(config, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def document_base(sample_id: str, path: Path, fmt: str, parser: str,
                  parser_version: str | None, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "experiment_id": "TECH-STRUCT-002-R01",
        "sample_id": sample_id,
        "doc_id": f"{sample_id.lower()}-{sha256(path)[:12]}",
        "source_path": str(path.relative_to(ROOT)),
        "source_hash": sha256(path),
        "source_format": fmt,
        "parser_name": parser,
        "parser_version": parser_version,
        "config": config,
        "config_hash": config_hash(config),
        "elements": [],
        "relations": [],
        "warnings": [],
    }


def add_element(document: dict[str, Any], *, element_type: str, text: str = "",
                parent_id: str | None = None, heading_path: list[str] | None = None,
                heading_level: int | None = None, role: str | None = None,
                reading_order_index: int | None = None, physical_page: int | None = None,
                printed_page_label: str | None = None, bbox: list[float] | None = None,
                char_start: int | None = None, char_end: int | None = None,
                source_line_start: int | None = None, source_line_end: int | None = None,
                style_ref: str | None = None, asset_ref: str | None = None,
                extra: dict[str, Any] | None = None) -> str:
    ordinal = len(document["elements"])
    element_id = f"{document['doc_id']}-e{ordinal + 1:04d}"
    element: dict[str, Any] = {
        "element_id": element_id,
        "element_type": element_type,
        "text": text,
        "normalized_text": normalize(text),
        "ordinal": ordinal,
        "parent_element_id": parent_id,
        "children_ids": [],
        "heading_path": list(heading_path or []),
        "heading_level": heading_level,
        "label": None,
        "role": role,
        "reading_order_index": reading_order_index if reading_order_index is not None else ordinal,
        "physical_page": physical_page,
        "printed_page_label": printed_page_label,
        "bbox": bbox,
        "char_start": char_start,
        "char_end": char_end,
        "source_line_start": source_line_start,
        "source_line_end": source_line_end,
        "column_id": None,
        "confidence": None,
        "confidence_by_field": {},
        "asset_ref": asset_ref,
        "style_ref": style_ref,
    }
    if extra:
        element.update(extra)
    document["elements"].append(element)
    if parent_id:
        for parent in document["elements"]:
            if parent["element_id"] == parent_id:
                parent["children_ids"].append(element_id)
                break
    return element_id


def build_txt(sample_id: str, path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    encoding = "utf-8"
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError:
        encoding = "gb18030"
        text = raw.decode(encoding)
    document = document_base(
        sample_id, path, "TXT", "explicit-encoding-baseline", None,
        {"encoding_fallback": ["utf-8", "gb18030"], "paragraph_rule": "blank_line"},
    )
    document["encoding"] = encoding
    lines = text.splitlines()
    cursor = 0
    paragraph_lines: list[tuple[int, str]] = []
    for line_number, line in enumerate(lines, start=1):
        if line.strip():
            paragraph_lines.append((line_number, line))
            continue
        if paragraph_lines:
            value = "\n".join(line for _, line in paragraph_lines)
            start = text.find(value, cursor)
            end = start + len(value) if start >= 0 else None
            add_element(
                document, element_type="paragraph", text=value,
                heading_path=[], reading_order_index=len(document["elements"]),
                char_start=start if start >= 0 else None, char_end=end,
                source_line_start=paragraph_lines[0][0], source_line_end=paragraph_lines[-1][0],
            )
            cursor = end if end is not None else cursor
            paragraph_lines = []
    if paragraph_lines:
        value = "\n".join(line for _, line in paragraph_lines)
        start = text.find(value, cursor)
        add_element(
            document, element_type="paragraph", text=value,
            heading_path=[], reading_order_index=len(document["elements"]),
            char_start=start if start >= 0 else None,
            char_end=start + len(value) if start >= 0 else None,
            source_line_start=paragraph_lines[0][0], source_line_end=paragraph_lines[-1][0],
        )
    document["warnings"].append("TXT has no native heading or semantic paragraph model; blank-line groups are a baseline only.")
    return finalize(document)


def build_markdown(sample_id: str, path: Path) -> dict[str, Any]:
    from markdown_it import MarkdownIt

    source = path.read_text(encoding="utf-8")
    document = document_base(
        sample_id, path, "Markdown", "markdown-it-py", version("markdown-it-py"),
        {"mode": "commonmark", "gfm_extensions": False},
    )
    tokens = MarkdownIt("commonmark").parse(source)
    heading_stack: list[tuple[int, str, str]] = []
    cursor = 0
    index = 0
    while index < len(tokens):
        token = tokens[index]
        line_start = (token.map[0] + 1) if token.map else None
        line_end = token.map[1] if token.map else None
        if token.type == "heading_open":
            level = int(token.tag[1:])
            inline = tokens[index + 1] if index + 1 < len(tokens) else None
            text = inline.content if inline and inline.type == "inline" else ""
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            parent_id = heading_stack[-1][2] if heading_stack else None
            element_id = add_element(
                document, element_type="heading", text=text, parent_id=parent_id,
                heading_path=[item[1] for item in heading_stack] + [text],
                heading_level=level, role="title" if level == 1 else "section_heading",
                source_line_start=line_start, source_line_end=line_end,
            )
            heading_stack.append((level, text, element_id))
            index += 3
            continue
        if token.type in {"paragraph_open", "blockquote_open"}:
            inline = tokens[index + 1] if index + 1 < len(tokens) else None
            text = inline.content if inline and inline.type == "inline" else ""
            if text:
                start = source.find(text, cursor)
                add_element(
                    document, element_type="paragraph" if token.type == "paragraph_open" else "blockquote",
                    text=text, parent_id=heading_stack[-1][2] if heading_stack else None,
                    heading_path=[item[1] for item in heading_stack],
                    source_line_start=line_start, source_line_end=line_end,
                    char_start=start if start >= 0 else None,
                    char_end=start + len(text) if start >= 0 else None,
                )
                cursor = start + len(text) if start >= 0 else cursor
            index += 3
            continue
        if token.type in {"code_block", "fence"}:
            add_element(
                document, element_type="code_block", text=token.content,
                parent_id=heading_stack[-1][2] if heading_stack else None,
                heading_path=[item[1] for item in heading_stack],
                source_line_start=line_start, source_line_end=line_end,
                extra={"language": token.info.strip() or None},
            )
        index += 1
    document["warnings"].append("CommonMark mode does not parse GFM tables, footnotes, or math extensions in this run.")
    return finalize(document)


def iter_docx_blocks(document: Any) -> Iterable[Any]:
    from docx.document import Document as DocumentClass
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P

    parent = document.element.body
    for child in parent.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def build_docx(sample_id: str, path: Path) -> dict[str, Any]:
    from docx import Document
    from docx.table import Table

    document = document_base(
        sample_id, path, "DOCX", "python-docx", version("python-docx"),
        {"paragraph_source": "body_xml_order", "visual_pagination": False},
    )
    heading_stack: list[tuple[int, str, str]] = []
    for block in iter_docx_blocks(Document(path)):
        if isinstance(block, Table):
            table_id = add_element(
                document, element_type="table", parent_id=heading_stack[-1][2] if heading_stack else None,
                heading_path=[item[1] for item in heading_stack],
                extra={"row_count": len(block.rows), "column_count": max((len(row.cells) for row in block.rows), default=0)},
            )
            for row_index, row in enumerate(block.rows):
                for col_index, cell in enumerate(row.cells):
                    add_element(
                        document, element_type="table_cell", text=cell.text, parent_id=table_id,
                        heading_path=[item[1] for item in heading_stack],
                        source_line_start=None, source_line_end=None,
                        extra={"row_index": row_index, "col_index": col_index, "rowspan": 1, "colspan": 1},
                    )
            continue
        style = block.style.name if block.style else None
        match = re.search(r"Heading\s+([1-9])$", style or "", re.IGNORECASE)
        is_title = (style or "").lower() == "title"
        if match or is_title:
            level = 0 if is_title else int(match.group(1))
            while heading_stack and heading_stack[-1][0] >= max(level, 1):
                heading_stack.pop()
            text = block.text
            element_id = add_element(
                document, element_type="heading", text=text,
                parent_id=heading_stack[-1][2] if heading_stack else None,
                heading_path=[item[1] for item in heading_stack] + [text],
                heading_level=level, role="title" if is_title else "section_heading",
                source_line_start=block._p.getparent().index(block._p) + 1,
                source_line_end=block._p.getparent().index(block._p) + 1,
                style_ref=style,
            )
            heading_stack.append((max(level, 1), text, element_id))
        elif block.text.strip():
            position = block._p.getparent().index(block._p) + 1
            add_element(
                document, element_type="paragraph", text=block.text,
                parent_id=heading_stack[-1][2] if heading_stack else None,
                heading_path=[item[1] for item in heading_stack],
                source_line_start=position, source_line_end=position, style_ref=style,
            )
    document["warnings"].extend([
        "python-docx logical parsing does not provide final visual page numbers or bboxes.",
        "Footnotes, text boxes, list semantics, and rendered header/footer positions need separate validation.",
    ])
    return finalize(document)


def build_pdf(sample_id: str, path: Path) -> dict[str, Any]:
    import fitz

    document = document_base(
        sample_id, path, "PDF", "PyMuPDF", version("PyMuPDF"),
        {"text_mode": "dict", "sort": False, "include_images": True},
    )
    cursor = 0
    with fitz.open(path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            page_dict = page.get_text("dict", sort=False)
            for block in page_dict.get("blocks", []):
                block_type = block.get("type", 0)
                if block_type == 1:
                    add_element(
                        document, element_type="figure", physical_page=page_number,
                        bbox=list(block.get("bbox", [])), asset_ref=f"{sample_id}:page-{page_number}:image",
                    )
                    continue
                lines = block.get("lines", [])
                text = "\n".join("".join(span.get("text", "") for span in line.get("spans", [])) for line in lines).strip()
                if not text:
                    continue
                start = cursor
                cursor += len(text) + 1
                add_element(
                    document, element_type="paragraph", text=text, physical_page=page_number,
                    bbox=list(block.get("bbox", [])), char_start=start, char_end=start + len(text),
                )
    document["warnings"].extend([
        "PyMuPDF blocks are low-level evidence and are not treated as semantic paragraphs or headings.",
        "Printed page labels, heading levels, footnotes, and table grids are not inferred in this adapter.",
    ])
    return finalize(document)


def finalize(document: dict[str, Any]) -> dict[str, Any]:
    counts = Counter(element["element_type"] for element in document["elements"])
    document["element_counts"] = dict(sorted(counts.items()))
    total = len(document["elements"])
    fields = ["physical_page", "bbox", "heading_path", "source_line_start", "char_start"]
    document["field_completeness"] = {
        field: (sum(element.get(field) is not None for element in document["elements"]) / total if total else 0.0)
        for field in fields
    }
    document["status"] = "scored" if total else "no_elements"
    return document


def build(sample_id: str) -> dict[str, Any]:
    path = FILES[sample_id]
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return build_pdf(sample_id, path)
    if suffix == ".docx":
        return build_docx(sample_id, path)
    if suffix == ".md":
        return build_markdown(sample_id, path)
    return build_txt(sample_id, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="append", choices=sorted(FILES), dest="samples")
    args = parser.parse_args()
    sample_ids = args.samples or list(FILES)
    RESULTS.mkdir(parents=True, exist_ok=True)
    outputs = []
    for sample_id in sample_ids:
        try:
            result = build(sample_id)
        except Exception as error:
            path = FILES[sample_id]
            result = {
                "experiment_id": "TECH-STRUCT-002-R01",
                "sample_id": sample_id,
                "source_path": str(path.relative_to(ROOT)),
                "source_hash": sha256(path),
                "status": "failed",
                "error_type": type(error).__name__,
                "error": str(error),
            }
        (RESULTS / f"{sample_id}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(result)
    summary = {
        "experiment_id": "TECH-STRUCT-002-R01",
        "date": __import__("time").strftime("%Y-%m-%d"),
        "python": sys.version,
        "samples": sample_ids,
        "outputs": outputs,
        "boundary": "Experimental IR mapping only; no production model migration or downstream quality claim.",
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
