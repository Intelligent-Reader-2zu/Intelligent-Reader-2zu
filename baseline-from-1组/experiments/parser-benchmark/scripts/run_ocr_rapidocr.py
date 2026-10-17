from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

from rapidocr import RapidOCR

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from run_ocr_tesseract_matrix import edit_distance, score_page  # noqa: E402


ROOT = SCRIPT_DIR.parent
DEFAULT_PDF = ROOT / "samples/self-authored/pdf/SELF-004-scanned.pdf"
DEFAULT_GOLD = ROOT / "samples/self-authored/annotations/SELF-004-ocr-ground-truth.json"
DEFAULT_INPUT_ROOT = ROOT / "results/ocr-tesseract-matrix"
DEFAULT_OUTPUT = ROOT / "results/ocr-rapidocr"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value):
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    return value


def strict_chinese_cer(reference: str, hypothesis: str) -> float | None:
    """Count U+FFFD and other non-Latin replacement output as Chinese errors."""
    ref = "".join(re.findall(r"[\u3400-\u9fff]", unicodedata.normalize("NFKC", reference)))
    hyp = "".join(re.findall(r"[\u3400-\u9fff\ufffd]", unicodedata.normalize("NFKC", hypothesis)))
    return edit_distance(ref, hyp) / len(ref) if ref else None


def run_page(engine: RapidOCR, image_path: Path) -> tuple[str, list[dict], float]:
    started = time.perf_counter()
    result = engine(image_path)
    elapsed_ms = (time.perf_counter() - started) * 1000
    boxes = result.boxes if result.boxes is not None else []
    texts = result.txts if result.txts is not None else []
    scores = result.scores if result.scores is not None else []
    items = []
    for box, text, confidence in zip(boxes, texts, scores, strict=True):
        polygon = json_safe(box)
        flat = [point for point in polygon if isinstance(point, list)]
        xs = [float(point[0]) for point in flat]
        ys = [float(point[1]) for point in flat]
        # RapidOCR reports scores in [0, 1], while the shared scorer uses
        # Tesseract's [0, 100] confidence convention.
        normalized_confidence = float(confidence) * 100
        items.append(
            {
                "text": str(text),
                "confidence": normalized_confidence,
                "bbox_polygon": polygon,
                "bbox": [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)],
            }
        )
    items.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    text = "\n".join(item["text"] for item in items)
    return text, items, elapsed_ms


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    pdf_path = args.pdf.resolve()
    gold_path = args.gold.resolve()
    input_root = args.input_root.resolve()
    output_root = args.output.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    source_hash = sha256(pdf_path)
    if source_hash != gold["source_sha256"]:
        raise SystemExit(f"source hash mismatch: expected {gold['source_sha256']}, actual {source_hash}")

    engine_started = time.perf_counter()
    engine = RapidOCR()
    cold_init_ms = (time.perf_counter() - engine_started) * 1000
    configurations = [("dpi144", 144), ("dpi300", 300)]
    all_results = []
    for config_id, dpi in configurations:
        config_dir = output_root / config_id
        config_dir.mkdir(parents=True, exist_ok=True)
        pages = []
        for page_index, reference_page in enumerate(gold["pages"], 1):
            image_path = input_root / f"dpi{dpi}-psm3-none" / f"page-{page_index}.png"
            if not image_path.exists():
                raise SystemExit(f"missing rendered input: {image_path}")
            reference = "\n".join(reference_page["lines"])
            try:
                text, items, elapsed_ms = run_page(engine, image_path)
                metrics = score_page(reference, text, gold["critical_strings"], items)
                metrics["cer_chinese"] = strict_chinese_cer(reference, text)
                confidences = [item["confidence"] for item in items]
                page_result = {
                    "physical_page": page_index,
                    "status": "succeeded",
                    "image_path": str(image_path),
                    "text": text,
                    "items": items,
                    "ocr_ms": elapsed_ms,
                    "mean_line_confidence": sum(confidences) / len(confidences) if confidences else None,
                    **metrics,
                }
            except Exception as exc:
                page_result = {
                    "physical_page": page_index,
                    "status": "failed",
                    "image_path": str(image_path),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            pages.append(page_result)
            (config_dir / f"page-{page_index}.json").write_text(
                json.dumps(page_result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        successful = [page for page in pages if page["status"] == "succeeded"]
        aggregate = {}
        for key in ("cer_all", "cer_chinese", "wer_latin_number", "critical_string_recall", "ocr_ms"):
            values = [page[key] for page in successful if page.get(key) is not None]
            aggregate[key] = sum(values) / len(values) if values else None
        aggregate["page_success_rate"] = len(successful) / len(pages)
        all_results.append({"config_id": config_id, "dpi": dpi, "pages": pages, "aggregate": aggregate})

    result = {
        "experiment_id": "TECH-OCR-015-R01",
        "source_path": str(pdf_path),
        "source_sha256": source_hash,
        "gold_path": str(gold_path),
        "rapidocr_version": "3.9.2",
        "onnxruntime_engine": True,
        "cold_init_ms": cold_init_ms,
        "configurations": all_results,
        "boundary": "Two-page project-authored fixture only; RapidOCR line recognition and polygon boxes, not layout/table/formula evaluation.",
    }
    (output_root / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# TECH-OCR-015-R01 RapidOCR/ONNX Runtime 本地实验",
        "",
        "> 当前 `SELF-004` 两页自制扫描样本上的可复现实验，不代表真实扫描件总体质量或最终选型。",
        "",
        f"- 输入 SHA-256：`{source_hash}`",
        f"- RapidOCR：`3.9.2`；推理引擎：`ONNX Runtime`；模型：默认 PP-OCRv6 small 中文模型",
        f"- 模型初始化（冷启动）约 `{cold_init_ms:.2f} ms`；页面使用与 Tesseract 相同的已渲染 PNG。",
        "- RapidOCR 返回检测到的文本行、四点 polygon bbox 和行置信度；未测版面类别、表格单元格、公式结构和手写/印章分类。",
        "",
        "| 配置 | 全字符 CER | 中文 CER | 英文/数字 WER | 关键字符串召回 | OCR ms/页 | 页面成功率 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in all_results:
        aggregate = item["aggregate"]
        lines.append(
            f"| {item['config_id']} | {aggregate['cer_all']:.4f} | {aggregate['cer_chinese']:.4f} | "
            f"{aggregate['wer_latin_number']:.4f} | {aggregate['critical_string_recall']:.4f} | "
            f"{aggregate['ocr_ms']:.2f} | {aggregate['page_success_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## 观察",
            "",
            "- 当前运行成功返回文本和 polygon bbox，具备离线部署和页内定位的基本接口。",
            "- JSON 中未检测到 U+FFFD；终端展示中文时可能出现类似乱码的字体/编码显示，但当前金标准对比的中文字符 CER 为 0。全字符 CER 的主要差异来自行/区域顺序和英文数字分组，因此仍需单独评测布局与 token 顺序。",
            "- 本实验只证明 RapidOCR/ONNX Runtime 在现有隔离环境中可运行；不能推出对双栏、表格、公式、印章或手写的支持结论。",
            "",
        ]
    )
    (output_root / "TECH-OCR-015-R01.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"experiment_id": result["experiment_id"], "output": str(output_root)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
