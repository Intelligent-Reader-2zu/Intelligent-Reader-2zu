from __future__ import annotations

import json
import hashlib
import re
import unicodedata
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/ocr-ppstructure-v3"
GOLD = ROOT / "samples/self-authored/annotations/SELF-004-ocr-ground-truth.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"}:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


def edit_distance(reference, hypothesis) -> int:
    previous = list(range(len(hypothesis) + 1))
    for index, ref_item in enumerate(reference, 1):
        current = [index]
        for hyp_index, hyp_item in enumerate(hypothesis, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[hyp_index] + 1,
                    previous[hyp_index - 1] + (ref_item != hyp_item),
                )
            )
        previous = current
    return previous[-1]


def rate(reference, hypothesis) -> float | None:
    return edit_distance(reference, hypothesis) / len(reference) if reference else None


def normalize_cer(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def chinese_characters(text: str) -> str:
    return "".join(re.findall(r"[\u3400-\u9fff]", unicodedata.normalize("NFKC", text)))


def latin_number_tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    return re.findall(r"[a-z]+(?:-[a-z0-9]+)*|\d+(?:\.\d+)?", normalized)


def main() -> None:
    page_layout = json.loads((OUT / "SELF-002-page-1-R02.json").read_text(encoding="utf-8"))
    page_scan_failure = json.loads((OUT / "SELF-004-page-1-R02.json").read_text(encoding="utf-8"))
    page_scan_small = json.loads((OUT / "SELF-004-page-1-1000px-R03.json").read_text(encoding="utf-8"))
    r03 = json.loads((OUT / "result-R03.json").read_text(encoding="utf-8"))
    gold = json.loads(GOLD.read_text(encoding="utf-8"))

    for page, filename in (
        (page_layout, "SELF-002-page-1-R02.json"),
        (page_scan_failure, "SELF-004-page-1-R02.json"),
        (page_scan_small, "SELF-004-page-1-1000px-R03.json"),
    ):
        page["input_sha256"] = sha256(Path(page["image_path"]))
        (OUT / filename).write_text(
            json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    layout_res = page_layout["outputs"][0]["res"]
    table = layout_res["table_res_list"][0]
    parser = TableParser()
    parser.feed(table["pred_html"])
    expected_rows = [
        ["字段", "示例值", "风险"],
        ["physical_page", "2", "封面导致打印页码偏移"],
        ["heading_path", "1 > 2", "标题层级可能被误判"],
    ]
    comparable_cells = [
        (expected, actual)
        for expected_row, actual_row in zip(expected_rows, parser.rows)
        for expected, actual in zip(expected_row, actual_row)
    ]

    scan_res = page_scan_small["outputs"][0]["res"]
    ocr_res = scan_res["overall_ocr_res"]
    reference = "\n".join(gold["pages"][0]["lines"])
    hypothesis = "\n".join(ocr_res["rec_texts"])
    normalized_hypothesis = normalize_cer(hypothesis).lower()
    critical_hits = {
        item: normalize_cer(item).lower() in normalized_hypothesis
        for item in gold["critical_strings"]
    }

    summary = {
        "experiment_ids": ["TECH-OCR-020-R02", "TECH-OCR-020-R03"],
        "r02": {
            "self_002_page_1": {
                "status": page_layout["status"],
                "elapsed_ms": page_layout["elapsed_ms"],
                "layout_label_counts": dict(
                    Counter(item["label"] for item in layout_res["layout_det_res"]["boxes"])
                ),
                "parsing_block_count": len(layout_res["parsing_res_list"]),
                "ordered_block_count": sum(
                    item["block_order"] is not None for item in layout_res["parsing_res_list"]
                ),
                "table_count": len(layout_res["table_res_list"]),
                "table_cell_box_count": len(table["cell_box_list"]),
                "expected_table_shape": [3, 3],
                "html_table_shape": [len(parser.rows), [len(row) for row in parser.rows]],
                "html_cells_in_correct_position": sum(
                    expected == actual for expected, actual in comparable_cells
                ),
                "html_cell_count": len(comparable_cells),
                "html_cell_position_accuracy": sum(
                    expected == actual for expected, actual in comparable_cells
                )
                / len(comparable_cells),
                "observed_html_rows": parser.rows,
            },
            "self_004_page_1": page_scan_failure,
        },
        "r03": {
            "sample_id": page_scan_small["sample_id"],
            "input_size": [scan_res["width"], scan_res["height"]],
            "model_init_ms": r03["model_init_ms"],
            "elapsed_ms": page_scan_small["elapsed_ms"],
            "cer_all": rate(normalize_cer(reference), normalize_cer(hypothesis)),
            "cer_chinese": rate(chinese_characters(reference), chinese_characters(hypothesis)),
            "wer_latin_number": rate(latin_number_tokens(reference), latin_number_tokens(hypothesis)),
            "critical_string_recall": sum(critical_hits.values()) / len(critical_hits),
            "critical_string_hits": critical_hits,
            "line_bbox_coverage": len(ocr_res["rec_boxes"]) / len(ocr_res["rec_texts"]),
            "layout_label_counts": dict(
                Counter(item["label"] for item in scan_res["layout_det_res"]["boxes"])
            ),
            "table_count": len(scan_res.get("table_res_list", [])),
        },
        "model_cache": {
            "file_count": 48,
            "bytes": 944516233,
        },
        "source_pdf_sha256": gold["source_sha256"],
        "boundary": "R02/R03 are smoke tests on project-authored pages. R03 is a downscaled diagnostic and must not be mixed with the original-resolution quality matrix.",
    }
    (OUT / "score-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    aggregate = {
        "experiment_id": "TECH-OCR-020-R02",
        "status": "partial_or_failed",
        "paddleocr_version": r03["paddleocr_version"],
        "paddle_version": r03["paddle_version"],
        "python_version": r03["python_version"],
        "settings": {**r03["settings"]},
        "model_init_ms": None,
        "samples": [page_layout, page_scan_failure],
        "boundary": "Two project-authored pages; successful table/layout smoke test plus a reproduced native process exit on the original-resolution scan.",
    }
    (OUT / "result-R02.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"status": "succeeded", "output": str(OUT / "score-summary.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
