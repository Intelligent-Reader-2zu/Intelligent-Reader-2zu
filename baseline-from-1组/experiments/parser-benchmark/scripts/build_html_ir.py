"""Build a conservative DOM-based IR for the self-authored HTML fixture."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "samples" / "self-authored" / "html" / "SELF-012-noisy.html"
OUT = ROOT / "results" / "text-structure" / "ir" / "SELF-012.html.json"


def build() -> dict[str, Any]:
    source = SOURCE.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    soup = BeautifulSoup(source, "html.parser")
    doc: dict[str, Any] = {
        "experiment_id": "TECH-STRUCT-007-R01", "sample_id": "SELF-012",
        "doc_id": f"self-012-{source_hash[:12]}", "source_path": str(SOURCE.relative_to(ROOT)),
        "source_hash": source_hash, "source_format": "HTML", "parser_name": "BeautifulSoup DOM baseline",
        "parser_version": None, "config": {"root": "article", "noise_tags": ["nav", "aside", "script", "style"]},
        "elements": [], "relations": [], "warnings": [],
    }
    root = soup.find("article") or soup.body
    if root is None:
        doc["status"] = "no_article"
        return doc
    nodes = root.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "table", "pre", "figure"], recursive=True)
    heading_stack: list[tuple[int, str, str]] = []
    selector_counts: dict[str, int] = {}
    for node in nodes:
        if not isinstance(node, Tag):
            continue
        if node.name.startswith("h"):
            level = int(node.name[1:])
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            parent = heading_stack[-1][2] if heading_stack else None
            element_id = f"{doc['doc_id']}-e{len(doc['elements']) + 1:04d}"
            selector_counts[node.name] = selector_counts.get(node.name, 0) + 1
            selector = node.name + (f"#{node.get('id')}" if node.get("id") else f":nth-of-type({selector_counts[node.name]})")
            item = {"element_id": element_id, "element_type": "heading", "text": node.get_text(" ", strip=True), "heading_level": level, "heading_path": [x[1] for x in heading_stack] + [node.get_text(" ", strip=True)], "parent_element_id": parent, "source_selector": selector, "children_ids": []}
            doc["elements"].append(item)
            if parent:
                next(x for x in doc["elements"] if x["element_id"] == parent)["children_ids"].append(element_id)
            heading_stack.append((level, item["text"], element_id))
        elif node.name == "table":
            element_id = f"{doc['doc_id']}-e{len(doc['elements']) + 1:04d}"
            rows = node.find_all("tr")
            selector_counts[node.name] = selector_counts.get(node.name, 0) + 1
            item = {"element_id": element_id, "element_type": "table", "text": node.get_text(" ", strip=True), "heading_path": [x[1] for x in heading_stack], "row_count": len(rows), "column_count": max((len(row.find_all(["th", "td"], recursive=False)) for row in rows), default=0), "source_selector": f"table:nth-of-type({selector_counts[node.name]})", "children_ids": []}
            doc["elements"].append(item)
            for row_index, row in enumerate(rows):
                for col_index, cell in enumerate(row.find_all(["th", "td"], recursive=False)):
                    cell_id = f"{doc['doc_id']}-e{len(doc['elements']) + 1:04d}"
                    doc["elements"].append({"element_id": cell_id, "element_type": "table_cell", "text": cell.get_text(" ", strip=True), "parent_element_id": element_id, "row_index": row_index, "col_index": col_index, "children_ids": []})
                    item["children_ids"].append(cell_id)
                    doc["relations"].append({"relation_type": "table_contains_cell", "source_element_id": element_id, "target_element_id": cell_id, "evidence": "dom_table"})
        elif node.name == "pre":
            element_type = "code_block"
            selector_counts[node.name] = selector_counts.get(node.name, 0) + 1
            doc["elements"].append({"element_id": f"{doc['doc_id']}-e{len(doc['elements']) + 1:04d}", "element_type": element_type, "text": node.get_text(), "heading_path": [x[1] for x in heading_stack], "language": None, "source_selector": f"pre:nth-of-type({selector_counts[node.name]})", "children_ids": []})
        else:
            selector_counts[node.name] = selector_counts.get(node.name, 0) + 1
            suffix = f".{node.get('class')[0]}" if node.get("class") else f":nth-of-type({selector_counts[node.name]})"
            doc["elements"].append({"element_id": f"{doc['doc_id']}-e{len(doc['elements']) + 1:04d}", "element_type": "paragraph", "text": node.get_text(" ", strip=True), "heading_path": [x[1] for x in heading_stack], "source_selector": node.name + suffix, "children_ids": []})
    noise = []
    for node in soup.find_all(["nav", "aside", "script", "style", "footer"]):
        noise.append({"element_type": "noise" if node.name != "footer" else "footer", "text": node.get_text(" ", strip=True), "source_selector": node.name + (f".{node.get('class')[0]}" if node.get("class") else "")})
    doc["noise_elements"] = noise
    doc["relations"].append({"relation_type": "document_root", "source_element_id": doc["elements"][0]["element_id"] if doc["elements"] else None, "target_element_id": None, "evidence": "article_root"})
    doc["element_counts"] = {}
    for element in doc["elements"]:
        doc["element_counts"][element["element_type"]] = doc["element_counts"].get(element["element_type"], 0) + 1
    doc["noise_counts"] = {item["element_type"]: sum(x["element_type"] == item["element_type"] for x in noise) for item in noise}
    doc["status"] = "scored"
    doc["warnings"] = ["DOM baseline uses article as root; dynamic rendering and shadow DOM are not tested."]
    return doc


def main() -> None:
    result = build()
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"sample_id": result["sample_id"], "element_counts": result["element_counts"], "noise_counts": result["noise_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
