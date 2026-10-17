"""Build an experimental Markdown IR with table, footnote, math, and image nodes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples" / "self-authored" / "markdown"
IR_DIR = ROOT / "results" / "text-structure" / "ir"
FILES = {"SELF-008": SAMPLES / "SELF-008-complex.md", "SELF-009": SAMPLES / "SELF-009-heading-levels.md"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def add(document: dict[str, Any], kind: str, text: str = "", *, parent: str | None = None,
        path: list[str] | None = None, level: int | None = None,
        start: int | None = None, end: int | None = None, extra: dict[str, Any] | None = None) -> str:
    element_id = f"{document['doc_id']}-e{len(document['elements']) + 1:04d}"
    element = {
        "element_id": element_id, "element_type": kind, "text": text,
        "normalized_text": " ".join(text.split()), "ordinal": len(document["elements"]),
        "parent_element_id": parent, "children_ids": [], "heading_path": list(path or []),
        "heading_level": level, "label": None, "role": None,
        "reading_order_index": len(document["elements"]), "physical_page": None,
        "printed_page_label": None, "bbox": None, "char_start": None, "char_end": None,
        "source_line_start": start, "source_line_end": end, "column_id": None,
        "confidence": None, "confidence_by_field": {}, "asset_ref": None, "style_ref": None,
    }
    if extra:
        element.update(extra)
    document["elements"].append(element)
    if parent:
        for candidate in document["elements"]:
            if candidate["element_id"] == parent:
                candidate["children_ids"].append(element_id)
                break
    return element_id


def build(sample_id: str) -> dict[str, Any]:
    path = FILES[sample_id]
    source = path.read_text(encoding="utf-8")
    source_hash = sha256(path)
    doc: dict[str, Any] = {
        "experiment_id": "TECH-STRUCT-005-R01", "sample_id": sample_id,
        "doc_id": f"{sample_id.lower()}-{source_hash[:12]}",
        "source_path": str(path.relative_to(ROOT)), "source_hash": source_hash,
        "source_format": "Markdown", "parser_name": "markdown-it-py",
        "parser_version": None, "config": {"preset": "default", "table": True, "footnote": "source-regex", "math": "inline-regex"},
        "config_hash": hashlib.sha256(b"markdown-default-table-footnote-math").hexdigest()[:16],
        "elements": [], "relations": [], "warnings": [],
    }
    tokens = MarkdownIt("default").parse(source)
    headings: list[tuple[int, str, str]] = []
    definitions: dict[str, str] = {}
    definition_ids: dict[str, str] = {}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open":
            level = int(token.tag[1:])
            inline = tokens[i + 1]
            text = inline.content
            while headings and headings[-1][0] >= level:
                headings.pop()
            parent = headings[-1][2] if headings else None
            element_id = add(doc, "heading", text, parent=parent, path=[x[1] for x in headings] + [text], level=level, start=token.map[0] + 1, end=token.map[1])
            headings.append((level, text, element_id))
            i += 3
            continue
        if token.type == "table_open":
            table_id = add(doc, "table", parent=headings[-1][2] if headings else None, path=[x[1] for x in headings])
            row = -1
            col = 0
            i += 1
            while i < len(tokens) and tokens[i].type != "table_close":
                item = tokens[i]
                if item.type == "tr_open":
                    row += 1
                    col = 0
                elif item.type == "inline":
                    cell_id = add(doc, "table_cell", item.content, parent=table_id, path=[x[1] for x in headings], start=(item.map[0] + 1 if item.map else None), end=(item.map[1] if item.map else None), extra={"row_index": row, "col_index": col, "rowspan": 1, "colspan": 1})
                    doc["relations"].append({"relation_id": f"{doc['doc_id']}-r{len(doc['relations']) + 1:04d}", "relation_type": "table_contains_cell", "source_element_id": table_id, "target_element_id": cell_id, "evidence": "markdown_table_token"})
                    col += 1
                i += 1
            table = next(e for e in doc["elements"] if e["element_id"] == table_id)
            table["row_count"] = row + 1
            table["column_count"] = max((e.get("col_index", -1) for e in doc["elements"] if e.get("parent_element_id") == table_id), default=-1) + 1
            i += 1
            continue
        if token.type in {"paragraph_open", "blockquote_open"}:
            inline = tokens[i + 1] if i + 1 < len(tokens) else None
            if inline and inline.type == "inline":
                text = inline.content
                match = re.match(r"^\[\^([^\]]+)\]:\s*(.*)$", text)
                if match:
                    definitions[match.group(1)] = match.group(2)
                    element_id = add(doc, "footnote_definition", match.group(2), parent=headings[-1][2] if headings else None, path=[x[1] for x in headings], start=token.map[0] + 1, end=token.map[1])
                    definition_ids[match.group(1)] = element_id
                else:
                    element_id = add(doc, "paragraph" if token.type == "paragraph_open" else "blockquote", text, parent=headings[-1][2] if headings else None, path=[x[1] for x in headings], start=token.map[0] + 1, end=token.map[1])
                    for key in re.findall(r"\[\^([^\]]+)\]", text):
                        # Target is attached after definitions have been collected.
                        doc["relations"].append({"relation_id": f"pending:{element_id}:{key}", "relation_type": "footnote_marker_for", "source_element_id": element_id, "target_key": key, "evidence": "markdown_source_marker"})
                    for formula in re.findall(r"\$([^$]+)\$", text):
                        add(doc, "equation", formula, parent=element_id, path=[x[1] for x in headings], start=token.map[0] + 1, end=token.map[1], extra={"notation": "inline-latex"})
                    for alt, asset in re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", text):
                        figure_id = add(doc, "figure", alt, parent=element_id, path=[x[1] for x in headings], start=token.map[0] + 1, end=token.map[1], extra={"asset_ref": asset, "alt_text": alt})
                        doc["relations"].append({"relation_id": f"{doc['doc_id']}-r{len(doc['relations']) + 1:04d}", "relation_type": "caption_or_image_in", "source_element_id": element_id, "target_element_id": figure_id, "evidence": "markdown_image_token"})
            i += 3
            continue
        if token.type == "fence":
            add(doc, "code_block", token.content, parent=headings[-1][2] if headings else None, path=[x[1] for x in headings], start=token.map[0] + 1, end=token.map[1], extra={"language": token.info.strip() or None})
        i += 1
    for relation in doc["relations"]:
        if relation.get("relation_type") == "footnote_marker_for" and relation.get("target_key") in definition_ids:
            relation["target_element_id"] = definition_ids[relation["target_key"]]
            relation.pop("target_key", None)
            relation["relation_id"] = f"{doc['doc_id']}-r{len([x for x in doc['relations'] if x.get('relation_id','').startswith(doc['doc_id'])]) + 1:04d}"
        elif relation.get("relation_type") == "footnote_marker_for":
            relation["unresolved"] = True
    doc["relation_counts"] = {}
    for relation in doc["relations"]:
        kind = relation["relation_type"]
        doc["relation_counts"][kind] = doc["relation_counts"].get(kind, 0) + 1
    doc["element_counts"] = {}
    for element in doc["elements"]:
        kind = element["element_type"]
        doc["element_counts"][kind] = doc["element_counts"].get(kind, 0) + 1
    doc["warnings"].append("GFM tables are enabled through markdown-it default preset; footnotes and math use conservative source rules.")
    return doc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="append", choices=sorted(FILES), dest="samples")
    args = parser.parse_args()
    for sample_id in args.samples or list(FILES):
        doc = build(sample_id)
        (IR_DIR / f"{sample_id}.markdown-extended.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"sample_id": sample_id, "element_counts": doc["element_counts"], "relation_counts": doc["relation_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
