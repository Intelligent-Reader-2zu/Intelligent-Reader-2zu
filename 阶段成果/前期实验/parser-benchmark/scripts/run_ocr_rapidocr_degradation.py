from __future__ import annotations

import hashlib
import importlib.metadata
import json
import time
from pathlib import Path

from rapidocr import RapidOCR

from run_ocr_rapidocr import run_page, strict_chinese_cer
from run_ocr_tesseract_matrix import score_page

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "samples/self-authored/pdf/SELF-004-scanned.pdf"
GOLD = ROOT / "samples/self-authored/annotations/SELF-004-ocr-ground-truth.json"
INPUT = ROOT / "results/ocr-degradation-matrix"
OUT = ROOT / "results/ocr-rapidocr-degradation"
VARIANTS = ("base300", "downsample150", "blur", "low_contrast_noise", "rotate3")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    source_hash = sha256(PDF)
    if source_hash != gold["source_sha256"]:
        raise SystemExit(
            f"source hash mismatch: expected {gold['source_sha256']}, actual {source_hash}"
        )

    started = time.perf_counter()
    engine = RapidOCR()
    init_ms = (time.perf_counter() - started) * 1000
    variants = []
    for variant in VARIANTS:
        variant_dir = OUT / variant
        variant_dir.mkdir(parents=True, exist_ok=True)
        pages = []
        for page_no, gold_page in enumerate(gold["pages"], 1):
            image_path = INPUT / variant / f"page-{page_no}.png"
            reference = "\n".join(gold_page["lines"])
            try:
                text, items, elapsed_ms = run_page(engine, image_path)
                metrics = score_page(reference, text, gold["critical_strings"], items)
                metrics["cer_chinese"] = strict_chinese_cer(reference, text)
                page = {
                    "physical_page": page_no,
                    "status": "succeeded",
                    "image_path": str(image_path),
                    "input_sha256": sha256(image_path),
                    "text": text,
                    "items": items,
                    "ocr_ms": elapsed_ms,
                    **metrics,
                }
            except Exception as exc:
                page = {
                    "physical_page": page_no,
                    "status": "failed",
                    "image_path": str(image_path),
                    "input_sha256": sha256(image_path),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            pages.append(page)
            (variant_dir / f"page-{page_no}.json").write_text(
                json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        successful = [page for page in pages if page["status"] == "succeeded"]
        aggregate = {
            key: mean([page[key] for page in successful if page.get(key) is not None])
            for key in (
                "cer_all",
                "cer_chinese",
                "wer_latin_number",
                "critical_string_recall",
                "mean_word_confidence",
                "low_confidence_word_ratio",
                "words_with_bbox_ratio",
                "ocr_ms",
            )
        }
        aggregate["page_success_rate"] = len(successful) / len(pages)
        variants.append({"variant": variant, "pages": pages, "aggregate": aggregate})

    report = {
        "experiment_id": "TECH-OCR-021-R01",
        "source_path": str(PDF),
        "source_sha256": source_hash,
        "gold_path": str(GOLD),
        "rapidocr_version": importlib.metadata.version("rapidocr"),
        "onnxruntime_version": importlib.metadata.version("onnxruntime"),
        "model_init_ms": init_ms,
        "variants": variants,
        "boundary": "Two-page project-authored fixture with synthetic transformations; line OCR and polygon bboxes only.",
    }
    (OUT / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# TECH-OCR-021-R01 RapidOCR 退化矩阵",
        "",
        "> 与 TECH-OCR-002 使用完全相同的五组项目自制页面图。结果只用于一期轻度退化范围判断，不代表真实扫描件总体分布。",
        "",
        f"- RapidOCR `{report['rapidocr_version']}`；ONNX Runtime `{report['onnxruntime_version']}`；CPU",
        f"- SELF-004 SHA-256：`{source_hash}`",
        f"- 本地模型初始化约 `{init_ms:.2f} ms`；页面时延不含 PDF 渲染和首次模型下载",
        "",
        "| 变体 | 全字符 CER | 中文 CER | 英文/数字 WER | 关键字符串召回 | bbox 覆盖 | OCR ms/页 | 页面成功率 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in variants:
        aggregate = item["aggregate"]
        lines.append(
            f"| {item['variant']} | {aggregate['cer_all']:.4f} | {aggregate['cer_chinese']:.4f} | "
            f"{aggregate['wer_latin_number']:.4f} | {aggregate['critical_string_recall']:.4f} | "
            f"{aggregate['words_with_bbox_ratio']:.4f} | {aggregate['ocr_ms']:.2f} | "
            f"{aggregate['page_success_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## 判读边界",
            "",
            "- 关键字符串召回按页面平均；数字、编号和英文 token 错误仍须看 WER，不能只看中文 CER。",
            "- 合成模糊、降采样和旋转只能说明相对敏感性。真实折痕、印章、手写和遮挡仍未覆盖。",
            "- bbox 覆盖表示输出带定位，不表示框一定覆盖正确字符，也不表示布局阅读顺序正确。",
            "",
        ]
    )
    (OUT / "TECH-OCR-021-R01.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"experiment_id": report["experiment_id"], "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
