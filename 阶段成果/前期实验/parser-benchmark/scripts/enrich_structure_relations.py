"""Add conservative, text-derived relations to experimental IR JSON files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
IR_DIR = ROOT / "results" / "text-structure" / "ir"
SAMPLES = ROOT / "samples" / "self-authored"


def add_relation(document: dict[str, Any], relation_type: str, source: str, target: str | None,
                 key: str | None = None) -> None:
    if target is None:
        return
    relation = {
        "relation_id": f"{document['doc_id']}-r{len(document['relations']) + 1:04d}",
        "relation_type": relation_type,
        "source_element_id": source,
        "target_element_id": target,
        "confidence": None,
        "evidence": "text_or_parent_link",
    }
    if key is not None:
        relation["key"] = key
    document["relations"].append(relation)


def by_id(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {element["element_id"]: element for element in document["elements"]}


def enrich_parent_and_tables(document: dict[str, Any]) -> None:
    elements = by_id(document)
    for element in document["elements"]:
        parent_id = element.get("parent_element_id")
        if parent_id:
            add_relation(document, "contains", parent_id, element["element_id"])
        if element.get("element_type") == "table":
            for child_id in element.get("children_ids", []):
                add_relation(document, "table_contains_cell", element["element_id"], child_id)


def enrich_markdown(document: dict[str, Any], source_path: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    elements = by_id(document)
    definitions: dict[str, str] = {}
    definition_lines: dict[str, int] = {}
    for line_number, line in enumerate(source.splitlines(), start=1):
        match = re.match(r"^\[\^([^\]]+)\]:\s*(.*)$", line)
        if match:
            definitions[match.group(1)] = match.group(2)
            definition_lines[match.group(1)] = line_number

    for element in document["elements"]:
        text = element.get("text", "")
        for key in re.findall(r"\[\^([^\]]+)\]", text):
            line = element.get("source_line_start") or 0
            if line == definition_lines.get(key) or re.match(rf"^\[\^{re.escape(key)}\]:", text.strip()):
                continue
            target = next(
                (candidate["element_id"] for candidate in document["elements"]
                 if candidate.get("source_line_start") == definition_lines.get(key)),
                None,
            )
            add_relation(document, "footnote_marker_for", element["element_id"], target, key)
        for key in re.findall(r"(?<!\^)(?<!\w)\[(\d+)\]", text):
            target = next(
                (candidate["element_id"] for candidate in document["elements"]
                 if re.match(rf"^\[{re.escape(key)}\]", candidate.get("text", "").strip())),
                None,
            )
            add_relation(document, "citation_refers_to", element["element_id"], target, key)
    if definitions and not any(relation["relation_type"] == "footnote_marker_for" for relation in document["relations"]):
        document["warnings"].append("Footnote definitions were found in source, but no parsed marker relation could be attached.")


def enrich(document: dict[str, Any]) -> dict[str, Any]:
    document["relations"] = []
    enrich_parent_and_tables(document)
    if document.get("source_format") == "Markdown":
        enrich_markdown(document, ROOT / document["source_path"])
    document["relation_counts"] = {}
    for relation in document["relations"]:
        kind = relation["relation_type"]
        document["relation_counts"][kind] = document["relation_counts"].get(kind, 0) + 1
    document["relation_policy"] = "conservative; no relation is emitted without a source or target element"
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="append", dest="samples")
    args = parser.parse_args()
    paths = sorted(IR_DIR.glob("SELF-*.json"))
    selected = set(args.samples or [path.stem for path in paths])
    outputs = []
    for path in paths:
        if path.stem not in selected:
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        enriched = enrich(document)
        path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append({
            "sample_id": enriched.get("sample_id"),
            "relation_counts": enriched.get("relation_counts", {}),
            "warnings": enriched.get("warnings", []),
        })
    summary = {
        "experiment_id": "TECH-STRUCT-003-R01",
        "outputs": outputs,
        "boundary": "Relations are emitted only when source and target elements are observable; unresolved references remain warnings.",
    }
    out = IR_DIR / "relation-summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
