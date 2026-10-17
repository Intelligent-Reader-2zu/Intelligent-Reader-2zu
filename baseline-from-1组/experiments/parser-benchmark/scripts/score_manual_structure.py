"""Score parser outputs against user-confirmed non-OCR structure annotations."""

from __future__ import annotations

import collections
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "text-structure"
MANUAL = RESULTS / "manual-annotations"
SAMPLE_IDS = ["SELF-001", "SELF-002", "SELF-003"]


def normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).replace("|", "")
    return re.sub(r"\s+", "", normalized).casefold()


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def counter_recall(reference: str, candidate: str) -> float | None:
    reference_counts = collections.Counter(normalize(reference))
    candidate_counts = collections.Counter(normalize(candidate))
    matched = sum(min(count, candidate_counts[char]) for char, count in reference_counts.items())
    return ratio(matched, sum(reference_counts.values()))


def text_from_pymupdf_block(block: dict[str, Any]) -> str:
    return "\n".join(
        "".join(span.get("text", "") for span in line.get("spans", []))
        for line in block.get("lines", [])
    )


def pymupdf_output(sample_id: str) -> dict[str, Any]:
    result = json.loads((RESULTS / "pymupdf" / f"{sample_id}.json").read_text(encoding="utf-8"))
    elements = []
    for page in result.get("pages", []):
        for block in page.get("dict", {}).get("blocks", []):
            if "lines" not in block:
                continue
            elements.append(
                {
                    "text": text_from_pymupdf_block(block),
                    "label": "layout_text_block",
                    "page": page["physical_page"],
                    "bbox": block.get("bbox"),
                }
            )
    return {
        "parser": "PyMuPDF",
        "parser_version": result.get("parser_version"),
        "source_sha256": result.get("source_sha256"),
        "elements": elements,
        "tables": [],
        "semantic_heading_labels": False,
        "semantic_footnote_labels": False,
        "table_grid_available": False,
    }


def docling_output(sample_id: str) -> dict[str, Any]:
    result = json.loads((RESULTS / "docling" / f"{sample_id}.json").read_text(encoding="utf-8"))
    raw = json.loads((RESULTS / "docling" / f"{sample_id}.docling.json").read_text(encoding="utf-8"))
    texts = raw.get("texts", [])
    tables = raw.get("tables", [])
    groups = raw.get("groups", [])

    def resolve(reference: dict[str, str]) -> list[dict[str, Any]]:
        pointer = reference.get("$ref", "")
        if pointer.startswith("#/texts/"):
            item = texts[int(pointer.rsplit("/", 1)[1])]
            prov = (item.get("prov") or [{}])[0]
            bbox = prov.get("bbox")
            return [{
                "text": item.get("text", ""),
                "label": item.get("label"),
                "page": prov.get("page_no"),
                "bbox": bbox,
            }]
        if pointer.startswith("#/tables/"):
            table = tables[int(pointer.rsplit("/", 1)[1])]
            grid = table.get("data", {}).get("grid", [])
            text = "\n".join(" | ".join(cell.get("text", "") for cell in row) for row in grid)
            prov = (table.get("prov") or [{}])[0]
            return [{"text": text, "label": "table", "page": prov.get("page_no"), "bbox": prov.get("bbox")}]
        if pointer.startswith("#/groups/"):
            group = groups[int(pointer.rsplit("/", 1)[1])]
            return [element for child in group.get("children", []) for element in resolve(child)]
        return []

    elements = [element for child in raw.get("body", {}).get("children", []) for element in resolve(child)]
    return {
        "parser": "Docling",
        "parser_version": result.get("parser_version"),
        "source_sha256": result.get("source_sha256"),
        "elements": elements,
        "tables": tables,
        "semantic_heading_labels": True,
        "semantic_footnote_labels": True,
        "table_grid_available": True,
    }


def tika_output(sample_id: str) -> dict[str, Any]:
    result = json.loads((RESULTS / "tika" / f"{sample_id}.json").read_text(encoding="utf-8"))
    text = result.get("text_preview", "")
    elements = [
        {"text": segment, "label": "plain_text_segment", "page": None, "bbox": None}
        for segment in re.split(r"\n\s*\n", text)
        if segment.strip()
    ]
    return {
        "parser": "Apache Tika",
        "parser_version": result.get("parser_version"),
        "source_sha256": result.get("source_sha256"),
        "elements": elements,
        "tables": [],
        "semantic_heading_labels": False,
        "semantic_footnote_labels": False,
        "table_grid_available": False,
    }


def locate_units(gold_units: list[dict[str, Any]], candidate_text: str) -> tuple[dict[str, int], list[str]]:
    normalized = normalize(candidate_text)
    positions: dict[str, int] = {}
    missing: list[str] = []
    for unit in gold_units:
        needle = normalize(unit["text"])
        position = normalized.find(needle)
        if position >= 0:
            positions[unit["unit_id"]] = position
        else:
            missing.append(unit["unit_id"])
    return positions, missing


def reading_order_score(gold_units: list[dict[str, Any]], positions: dict[str, int]) -> dict[str, Any]:
    located = [unit for unit in gold_units if unit["unit_id"] in positions]
    comparable = correct = 0
    for left_index, left in enumerate(located):
        for right in located[left_index + 1:]:
            comparable += 1
            if positions[left["unit_id"]] < positions[right["unit_id"]]:
                correct += 1
    return {
        "located_units": len(located),
        "gold_units": len(gold_units),
        "unit_coverage": ratio(len(located), len(gold_units)),
        "correct_pairs": correct,
        "comparable_pairs": comparable,
        "pairwise_accuracy": ratio(correct, comparable),
    }


def heading_score(annotation: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    if not output["semantic_heading_labels"]:
        return {"status": "not_available", "reason": "parser output has no semantic heading labels"}
    gold = {normalize(unit["text"]) for unit in annotation["units"] if unit["label"] == "heading"}
    predicted = {
        normalize(element["text"])
        for element in output["elements"]
        if element.get("label") in {"section_header", "title"}
    }
    matched = gold & predicted
    return {
        "status": "scored",
        "gold_count": len(gold),
        "predicted_count": len(predicted),
        "matched_count": len(matched),
        "precision": ratio(len(matched), len(predicted)),
        "recall": ratio(len(matched), len(gold)),
        "f1": ratio(2 * len(matched), len(gold) + len(predicted)),
    }


def paragraph_score(annotation: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    gold = {
        normalize(unit["text"])
        for unit in annotation["units"]
        if unit["label"] in {"subtitle", "paragraph", "reference"}
    }
    predicted = {normalize(element["text"]) for element in output["elements"] if element.get("text", "").strip()}
    matched = gold & predicted
    return {
        "status": "scored",
        "method": "exact normalized gold paragraph appears as one parser element",
        "gold_count": len(gold),
        "matched_count": len(matched),
        "exact_boundary_recall": ratio(len(matched), len(gold)),
    }


def footnote_score(annotation: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    gold = {normalize(unit["text"]) for unit in annotation["units"] if unit["label"] == "footnote"}
    if not output["semantic_footnote_labels"]:
        return {"status": "not_available", "gold_count": len(gold), "reason": "parser output has no semantic footnote labels"}
    predicted = {
        normalize(element["text"])
        for element in output["elements"]
        if element.get("label") in {"footnote", "footnote_ref"}
    }
    return {
        "status": "scored",
        "gold_count": len(gold),
        "matched_count": len(gold & predicted),
        "recall": ratio(len(gold & predicted), len(gold)),
    }


def footer_score(annotation: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    gold = [normalize(unit["text"]) for unit in annotation["units"] if unit["label"] == "footer"]
    all_text = normalize("\n".join(element["text"] for element in output["elements"]))
    present = sum(footer in all_text for footer in gold)
    classified = sum(
        normalize(element["text"]) in gold and element.get("label") in {"page_footer", "page_header"}
        for element in output["elements"]
    )
    downstream_body = normalize("\n".join(
        element["text"]
        for element in output["elements"]
        if element.get("label") not in {"page_footer", "page_header"}
    ))
    present_after_type_filter = sum(footer in downstream_body for footer in gold)
    return {
        "gold_footer_count": len(gold),
        "present_in_raw_output": present,
        "explicitly_classified_as_furniture": classified,
        "raw_output_exclusion_rate": ratio(len(gold) - present, len(gold)),
        "present_after_type_filter": present_after_type_filter,
        "type_filter_exclusion_rate": ratio(len(gold) - present_after_type_filter, len(gold)),
    }


def table_score(annotation: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    gold_tables = annotation.get("table_grids", [])
    if not output["table_grid_available"]:
        return {"status": "not_available", "gold_table_count": len(gold_tables), "reason": "parser output has no table grid"}
    predicted_tables = output["tables"]
    scores = []
    for index, gold in enumerate(gold_tables):
        if index >= len(predicted_tables):
            scores.append({"table_id": gold["table_id"], "status": "missing"})
            continue
        predicted = predicted_tables[index].get("data", {})
        predicted_grid = predicted.get("grid", [])
        predicted_cells = [cell for row in predicted_grid for cell in row]
        gold_cells = gold["cells"]
        correct_cells = sum(
            normalize(gold_cell["text"]) == normalize(predicted_cell.get("text", ""))
            for gold_cell, predicted_cell in zip(gold_cells, predicted_cells)
        )
        scores.append({
            "table_id": gold["table_id"],
            "status": "scored",
            "gold_rows": gold["rows"],
            "gold_columns": gold["columns"],
            "predicted_rows": predicted.get("num_rows"),
            "predicted_columns": predicted.get("num_cols"),
            "grid_shape_correct": predicted.get("num_rows") == gold["rows"] and predicted.get("num_cols") == gold["columns"],
            "gold_cell_count": len(gold_cells),
            "predicted_cell_count": len(predicted_cells),
            "position_aligned_cell_text_accuracy": ratio(correct_cells, len(gold_cells)),
        })
    return {"status": "scored", "tables": scores}


def score(sample_id: str, output: dict[str, Any]) -> dict[str, Any]:
    annotation = json.loads((MANUAL / f"{sample_id}.json").read_text(encoding="utf-8"))
    if annotation["source_sha256"] != output["source_sha256"]:
        raise ValueError(f"Source hash mismatch for {sample_id} / {output['parser']}")
    ordered_units = sorted(
        [
            unit for unit in annotation["units"]
            if unit.get("reading_order_rank") is not None and unit["label"] != "table"
        ],
        key=lambda unit: unit["reading_order_rank"],
    )
    candidate_text = "\n".join(element["text"] for element in output["elements"])
    gold_content = "\n".join(
        unit["text"] for unit in annotation["units"]
        if unit.get("reading_order_rank") is not None
    )
    positions, missing = locate_units(ordered_units, candidate_text)
    located_elements = [element for element in output["elements"] if element.get("text", "").strip()]
    return {
        "experiment_id": "TECH-DOC-007-R02-manual-score",
        "sample_id": sample_id,
        "parser": output["parser"],
        "parser_version": output["parser_version"],
        "source_sha256": output["source_sha256"],
        "content_character_recall": counter_recall(gold_content, candidate_text),
        "reading_order": reading_order_score(ordered_units, positions),
        "missing_order_unit_ids": missing,
        "paragraph_boundaries": paragraph_score(annotation, output),
        "headings": heading_score(annotation, output),
        "footnotes": footnote_score(annotation, output),
        "footers": footer_score(annotation, output),
        "tables": table_score(annotation, output),
        "location_fields": {
            "element_count": len(located_elements),
            "elements_with_page": sum(element.get("page") is not None for element in located_elements),
            "elements_with_bbox": sum(element.get("bbox") is not None for element in located_elements),
        },
        "boundary": "No OCR metrics. Missing semantic fields are not scored as success or failure.",
    }


def main() -> None:
    adapters = [pymupdf_output, docling_output, tika_output]
    outputs = [score(sample_id, adapter(sample_id)) for sample_id in SAMPLE_IDS for adapter in adapters]
    report = {
        "experiment_id": "TECH-DOC-007-R02-manual-score",
        "annotation_status": "three user-confirmed fixtures",
        "scope": "non-OCR text structure",
        "scoring_notes": {
            "content_character_recall": "character multiset recall after NFKC, case folding, and whitespace removal",
            "reading_order": "pairwise order among fully located non-table gold units; report coverage separately",
            "paragraph_boundaries": "exact normalized gold paragraph must appear as one parser element",
            "not_available": "parser did not expose the semantic field; not treated as pass or fail"
        },
        "outputs": outputs,
    }
    path = RESULTS / "manual-score.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
