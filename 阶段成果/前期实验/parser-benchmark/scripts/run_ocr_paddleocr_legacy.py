from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import statistics
import time
import unicodedata
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/ocr-paddleocr"
os.environ.setdefault("PADDLE_OCR_BASE_DIR", str(OUT / "model-cache"))

import paddle  # noqa: E402
from paddleocr import PaddleOCR  # noqa: E402

PDF = ROOT / "samples/self-authored/pdf/SELF-004-scanned.pdf"
GOLD = ROOT / "samples/self-authored/annotations/SELF-004-ocr-ground-truth.json"
INPUT = ROOT / "results/ocr-tesseract-matrix"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def score_page(reference: str, hypothesis: str, critical_strings: list[str], rows: list[dict]) -> dict:
    confidences = [row["confidence"] for row in rows]
    normalized_hypothesis = normalize_cer(hypothesis).lower()
    hits = {item: normalize_cer(item).lower() in normalized_hypothesis for item in critical_strings}
    return {
        "cer_all": rate(normalize_cer(reference), normalize_cer(hypothesis)),
        "cer_chinese": rate(chinese_characters(reference), chinese_characters(hypothesis)),
        "wer_latin_number": rate(latin_number_tokens(reference), latin_number_tokens(hypothesis)),
        "critical_string_recall": sum(hits.values()) / len(hits),
        "critical_string_hits": hits,
        "line_count": len(rows),
        "mean_line_confidence": sum(confidences) / len(confidences) if confidences else None,
        "low_confidence_line_ratio": sum(value < 60 for value in confidences) / len(confidences) if confidences else None,
        "lines_with_bbox_ratio": sum(all(value >= 0 for value in row["bbox"]) for row in rows) / len(rows) if rows else None,
    }


def parse_result(result) -> list[dict]:
    rows = []
    for page_result in result:
        if not page_result:
            continue
        for polygon, recognition in page_result:
            text, score = recognition
            points = polygon.tolist() if hasattr(polygon, "tolist") else polygon
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            rows.append(
                {
                    "text": str(text),
                    "confidence": float(score) * 100,
                    "bbox_polygon": points,
                    "bbox": [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)],
                }
            )
    rows.sort(key=lambda row: (row["bbox"][1], row["bbox"][0]))
    return rows


def nearest_percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(percentile * len(ordered) + 0.999999) - 1))
    return ordered[index]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    source_hash = sha256(PDF)
    if source_hash != gold["source_sha256"]:
        raise SystemExit(f"source hash mismatch: expected {gold['source_sha256']}, actual {source_hash}")

    started = time.perf_counter()
    ocr = PaddleOCR(use_angle_cls=False, lang="ch", show_log=False)
    init_ms = (time.perf_counter() - started) * 1000
    configurations = []
    for dpi in (144, 300):
        config_id = f"dpi{dpi}"
        config_dir = OUT / "r02" / config_id
        config_dir.mkdir(parents=True, exist_ok=True)
        pages = []
        for page_no, gold_page in enumerate(gold["pages"], 1):
            image = INPUT / f"dpi{dpi}-psm3-none" / f"page-{page_no}.png"
            started = time.perf_counter()
            try:
                image_data = cv2.imread(str(image))
                if image_data is None:
                    raise FileNotFoundError(image)
                timing_runs_ms = []
                raw_result = None
                for _ in range(5):
                    started = time.perf_counter()
                    current_result = ocr.ocr(image_data, cls=False)
                    timing_runs_ms.append((time.perf_counter() - started) * 1000)
                    if raw_result is None:
                        raw_result = current_result
                rows = parse_result(raw_result)
                text = "\n".join(row["text"] for row in rows)
                reference = "\n".join(gold_page["lines"])
                page = {
                    "physical_page": page_no,
                    "status": "succeeded",
                    "image": str(image),
                    "text": text,
                    "timing_runs_ms": timing_runs_ms,
                    "elapsed_ms_mean": sum(timing_runs_ms) / len(timing_runs_ms),
                    "elapsed_ms_p50": statistics.median(timing_runs_ms),
                    "elapsed_ms_p95": nearest_percentile(timing_runs_ms, 0.95),
                    "rows": rows,
                    **score_page(reference, text, gold["critical_strings"], rows),
                }
            except Exception as exc:
                page = {
                    "physical_page": page_no,
                    "status": "failed",
                    "image": str(image),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            pages.append(page)
            (config_dir / f"page-{page_no}.json").write_text(
                json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        successful = [page for page in pages if page["status"] == "succeeded"]
        aggregate = {"page_success_rate": len(successful) / len(pages)}
        for key in (
            "cer_all",
            "cer_chinese",
            "wer_latin_number",
            "critical_string_recall",
            "mean_line_confidence",
            "low_confidence_line_ratio",
            "lines_with_bbox_ratio",
        ):
            values = [page[key] for page in successful if page.get(key) is not None]
            aggregate[key] = sum(values) / len(values) if values else None
        timing_values = [value for page in successful for value in page["timing_runs_ms"]]
        aggregate["elapsed_ms_mean"] = sum(timing_values) / len(timing_values) if timing_values else None
        aggregate["elapsed_ms_p50"] = statistics.median(timing_values) if timing_values else None
        aggregate["elapsed_ms_p95"] = nearest_percentile(timing_values, 0.95)
        aggregate["timing_run_count"] = len(timing_values)
        configurations.append({"config_id": config_id, "dpi": dpi, "pages": pages, "aggregate": aggregate})

    report = {
        "experiment_id": "TECH-OCR-016-R02",
        "engine": "PaddleOCR",
        "version": importlib.metadata.version("paddleocr"),
        "paddle_version": paddle.__version__,
        "python_version": os.sys.version.split()[0],
        "source_sha256": source_hash,
        "model_init_ms": init_ms,
        "configurations": configurations,
        "status": "succeeded" if all(item["aggregate"]["page_success_rate"] == 1 for item in configurations) else "partial_or_failed",
        "boundary": "Two-page SELF-004 baseline only; no layout/table/formula evaluation.",
    }
    (OUT / "result-R02.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"experiment_id": report["experiment_id"], "output": str(OUT), "status": report["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
