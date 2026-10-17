"""Map Docling raw exports to the experimental structure IR."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "results" / "text-structure" / "docling"
IR_DIR = ROOT / "results" / "text-structure" / "ir"
SAMPLES = ROOT / "samples" / "self-authored" / "pdf"
SAMPLE_PATHS = {
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


def bbox(provenance: list[dict[str, Any]] | None) -> list[float] | None:
    if not provenance:
        return None
    value = provenance[0].get("bbox") or {}
    if not all(key in value for key in ("l", "t", "r", "b")):
        return None
    return [value["l"], value["t"], value["r"], value["b"]]


def add(document: dict[str, Any], element_type: str, text: str = "", *, label: str | None = None,
        role: str | None = None, page: int | None = None, box: list[float] | None = None,
        level: int | None = None, parent: str | None = None, extra: dict[str, Any] | None = None) -> str:
    element_id = f"{document['doc_id']}-e{len(document['elements']) + 1:04d}"
    item = {
        "element_id": element_id,
        "element_type": element_type,
        "text": text,
        "normalized_text": text,
        "ordinal": len(document["elements"]),
        "parent_element_id": parent,
        "children_ids": [],
        "heading_path": [],
        "heading_level": level,
        "label": label,
        "role": role,
        "reading_order_index": len(document["elements"]),
        "physical_page": page,
        "printed_page_label": None,
        "bbox": box,
        "char_start": None,
        "char_end": None,
        "source_line_start": None,
        "source_line_end": None,
        "column_id": None,
        "confidence": None,
        "confidence_by_field": {},
        "asset_ref": None,
        "style_ref": None,
    }
    if extra:
        item.update(extra)
    document["elements"].append(item)
    if parent:
        for candidate in document["elements"]:
            if candidate["element_id"] == parent:
                candidate["children_ids"].append(element_id)
                break
    return element_id


def map_docling(sample_id: str) -> dict[str, Any]:
    raw_path = RAW_DIR / f"{sample_id}.docling.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    source_path = SAMPLE_PATHS[sample_id]
    source_hash = sha256(source_path)
    document = {
        "experiment_id": "TECH-STRUCT-004-R01",
        "sample_id": sample_id,
        "doc_id": f"{sample_id.lower()}-{source_hash[:12]}",
        "source_path": str(source_path.relative_to(ROOT)),
        "source_hash": source_hash,
        "source_format": "PDF",
        "parser_name": "Docling",
        "parser_version": version("docling") or "2.130.0",
        "config": {"do_ocr": False, "do_table_structure": True, "do_formula_enrichment": False},
        "config_hash": hashlib.sha256(b"docling-text-only-table").hexdigest()[:16],
        "elements": [],
        "relations": [],
        "warnings": [],
    }
    refs: dict[str, str] = {}
    heading_stack: list[tuple[int, str, str]] = []
    for text in raw.get("texts", []):
        label = text.get("label")
        kind = "heading" if label == "section_header" else "footer" if label == "page_footer" else "paragraph"
        role = "title" if label == "section_header" else "footer" if label == "page_footer" else None
        provenance = text.get("prov") or []
        level = text.get("level") if label == "section_header" else None
        if label == "section_header":
            level = level or 1
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            parent = heading_stack[-1][2] if heading_stack else None
        else:
            parent = heading_stack[-1][2] if heading_stack and label not in {"page_footer"} else None
        element_id = add(
            document, kind, text.get("text", ""), label=label, role=role,
            page=provenance[0].get("page_no") if provenance else None,
            box=bbox(provenance), level=level, parent=parent,
        )
        element = document["elements"][-1]
        element["heading_path"] = [item[1] for item in heading_stack] + ([element["text"]] if label == "section_header" else [])
        if label == "section_header":
            heading_stack.append((level, element["text"], element_id))
        refs[text.get("self_ref", "")] = element_id
        if kind == "paragraph":
            formula_match = re.search(r"(?:公式(?:示例)?[:：]\s*)?([A-Za-z][A-Za-z0-9_@]*\s*=\s*[^。；;]+)", element["text"])
            if formula_match:
                formula_id = add(
                    document, "equation", formula_match.group(1).strip(),
                    parent=element_id, page=provenance[0].get("page_no") if provenance else None,
                    box=bbox(provenance),
                    extra={"notation": "conservative-inline-regex", "verified": False},
                )
                document["relations"].append({
                    "relation_id": f"{document['doc_id']}-r{len(document['relations']) + 1:04d}",
                    "relation_type": "contains_equation",
                    "source_element_id": element_id,
                    "target_element_id": formula_id,
                    "confidence": None,
                    "evidence": "inline_formula_regex",
                })
    for table in raw.get("tables", []):
        provenance = table.get("prov") or []
        data = table.get("data") or {}
        current_heading_path = [item[1] for item in heading_stack]
        table_id = add(
            document, "table", label="table",
            page=provenance[0].get("page_no") if provenance else None,
            box=bbox(provenance),
            extra={"row_count": data.get("num_rows"), "column_count": data.get("num_cols")},
        )
        document["elements"][-1]["heading_path"] = current_heading_path
        refs[table.get("self_ref", "")] = table_id
        cells = data.get("table_cells", [])
        for cell in cells:
            cell_box = cell.get("bbox") or {}
            cell_id = add(
                document, "table_cell", cell.get("text", ""), parent=table_id,
                page=provenance[0].get("page_no") if provenance else None,
                box=[cell_box.get("l"), cell_box.get("t"), cell_box.get("r"), cell_box.get("b")]
                if all(key in cell_box for key in ("l", "t", "r", "b")) else None,
                extra={
                    "row_index": cell.get("start_row_offset_idx"),
                    "col_index": cell.get("start_col_offset_idx"),
                    "rowspan": cell.get("row_span", 1),
                    "colspan": cell.get("col_span", 1),
                    "column_header": cell.get("column_header", False),
                },
            )
            document["elements"][-1]["heading_path"] = current_heading_path
            document["relations"].append({
                "relation_id": f"{document['doc_id']}-r{len(document['relations']) + 1:04d}",
                "relation_type": "table_contains_cell",
                "source_element_id": table_id,
                "target_element_id": cell_id,
                "confidence": None,
                "evidence": "docling_table_grid",
            })
    for element in document["elements"]:
        if element.get("parent_element_id"):
            document["relations"].append({
                "relation_id": f"{document['doc_id']}-r{len(document['relations']) + 1:04d}",
                "relation_type": "contains",
                "source_element_id": element["parent_element_id"],
                "target_element_id": element["element_id"],
                "confidence": None,
                "evidence": "docling_parent_link",
            })
    bibliography = [
        element for element in document["elements"]
        if re.match(r"^\[\d+\]", element.get("text", "").strip())
    ]
    for element in document["elements"]:
        for key in re.findall(r"(?<!\w)\[(\d+)\]", element.get("text", "")):
            target = next((item for item in bibliography if item["text"].lstrip().startswith(f"[{key}]")), None)
            if target and target["element_id"] != element["element_id"]:
                document["relations"].append({
                    "relation_id": f"{document['doc_id']}-r{len(document['relations']) + 1:04d}",
                    "relation_type": "citation_refers_to",
                    "source_element_id": element["element_id"],
                    "target_element_id": target["element_id"],
                    "key": key,
                    "confidence": None,
                    "evidence": "bracket_citation_regex",
                })
    document["relation_counts"] = {}
    for relation in document["relations"]:
        kind = relation["relation_type"]
        document["relation_counts"][kind] = document["relation_counts"].get(kind, 0) + 1
    document["element_counts"] = {}
    for element in document["elements"]:
        kind = element["element_type"]
        document["element_counts"][kind] = document["element_counts"].get(kind, 0) + 1
    total = len(document["elements"])
    document["field_completeness"] = {
        field: sum(element.get(field) is not None for element in document["elements"]) / total
        if total else 0.0
        for field in ("physical_page", "bbox", "heading_level")
    }
    document["status"] = "scored" if total else "no_elements"
    document["warnings"].append("Docling text/table export is mapped without OCR or formula enrichment.")
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="append", choices=sorted(SAMPLE_PATHS), dest="samples")
    args = parser.parse_args()
    samples = args.samples or list(SAMPLE_PATHS)
    IR_DIR.mkdir(parents=True, exist_ok=True)
    outputs = []
    for sample_id in samples:
        document = map_docling(sample_id)
        path = IR_DIR / f"{sample_id}.docling.json"
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append({
            "sample_id": sample_id,
            "element_counts": document["element_counts"],
            "relation_counts": document["relation_counts"],
            "field_completeness": document["field_completeness"],
        })
    summary = {
        "experiment_id": "TECH-STRUCT-004-R01",
        "outputs": outputs,
        "boundary": "Docling raw export mapping only; no OCR or formula accuracy claim.",
    }
    (IR_DIR / "docling-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
