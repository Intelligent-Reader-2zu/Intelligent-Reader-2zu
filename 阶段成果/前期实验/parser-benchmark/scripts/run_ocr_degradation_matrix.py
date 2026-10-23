from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import cv2
import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_ocr_tesseract_matrix import score_page, run_tesseract  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "samples/self-authored/pdf/SELF-004-scanned.pdf"
DEFAULT_GOLD = ROOT / "samples/self-authored/annotations/SELF-004-ocr-ground-truth.json"
DEFAULT_OUTPUT = ROOT / "results/ocr-degradation-matrix"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def transform(image: np.ndarray, variant: str) -> np.ndarray:
    if variant == "base300":
        return image
    if variant == "downsample150":
        height, width = image.shape[:2]
        half = cv2.resize(image, (width // 2, height // 2), interpolation=cv2.INTER_AREA)
        return cv2.resize(half, (width, height), interpolation=cv2.INTER_LINEAR)
    if variant == "blur":
        return cv2.GaussianBlur(image, (0, 0), sigmaX=1.6)
    if variant == "low_contrast_noise":
        rng = np.random.default_rng(20260928)
        gray = image.astype(np.float32)
        gray = (gray - 128.0) * 0.55 + 128.0
        noise = rng.normal(0.0, 7.0, gray.shape)
        return np.clip(gray + noise, 0, 255).astype(np.uint8)
    if variant == "rotate3":
        height, width = image.shape[:2]
        center = (width / 2, height / 2)
        matrix = cv2.getRotationMatrix2D(center, 3.0, 1.0)
        cosine = abs(matrix[0, 0])
        sine = abs(matrix[0, 1])
        new_width = int((height * sine) + (width * cosine))
        new_height = int((height * cosine) + (width * sine))
        matrix[0, 2] += (new_width / 2) - center[0]
        matrix[1, 2] += (new_height / 2) - center[1]
        return cv2.warpAffine(image, matrix, (new_width, new_height), borderValue=255)
    raise ValueError(f"unknown variant: {variant}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--language", default="chi_sim+eng")
    args = parser.parse_args()

    pdf_path = args.pdf.resolve()
    gold_path = args.gold.resolve()
    output_path = args.output.resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    source_hash = sha256(pdf_path)
    if source_hash != gold["source_sha256"]:
        raise SystemExit(f"source hash mismatch: expected {gold['source_sha256']}, actual {source_hash}")

    version = subprocess.run(
        ["tesseract", "--version"], capture_output=True, check=True, text=True, encoding="utf-8"
    ).stdout.splitlines()[0]
    variants = ["base300", "downsample150", "blur", "low_contrast_noise", "rotate3"]
    document = fitz.open(pdf_path)
    results = []
    for variant in variants:
        variant_dir = output_path / variant
        variant_dir.mkdir(parents=True, exist_ok=True)
        pages = []
        for page_index, (page, reference_page) in enumerate(zip(document, gold["pages"], strict=True), 1):
            source_pixmap = page.get_pixmap(dpi=300, alpha=False)
            source = cv2.imdecode(np.frombuffer(source_pixmap.tobytes("png"), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            transformed = transform(source, variant)
            image_path = variant_dir / f"page-{page_index}.png"
            cv2.imwrite(str(image_path), transformed)
            reference = "\n".join(reference_page["lines"])
            started = time.perf_counter()
            try:
                text, words, ocr_ms, stderr = run_tesseract(image_path, args.language, 3)
                metrics = score_page(reference, text, gold["critical_strings"], words)
                page_result = {
                    "physical_page": page_index,
                    "status": "succeeded",
                    "image_size": [int(transformed.shape[1]), int(transformed.shape[0])],
                    "ocr_ms": ocr_ms,
                    "elapsed_ms": (time.perf_counter() - started) * 1000,
                    "text": text,
                    "words": words,
                    "stderr": stderr.strip(),
                    **metrics,
                }
            except Exception as exc:
                page_result = {
                    "physical_page": page_index,
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "ocr_ms": None,
                    "elapsed_ms": (time.perf_counter() - started) * 1000,
                }
            pages.append(page_result)
            (variant_dir / f"page-{page_index}.json").write_text(
                json.dumps(page_result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        numeric_keys = ["cer_all", "cer_chinese", "wer_latin_number", "critical_string_recall", "mean_word_confidence", "elapsed_ms"]
        aggregate = {
            key: sum(page[key] for page in pages if page.get(key) is not None) / len([page for page in pages if page.get(key) is not None])
            for key in numeric_keys
        }
        aggregate["page_success_rate"] = sum(page["status"] == "succeeded" for page in pages) / len(pages)
        results.append({"variant": variant, "pages": pages, "aggregate": aggregate})

    result = {
        "experiment_id": "TECH-OCR-002-R01",
        "source_path": str(pdf_path),
        "source_sha256": source_hash,
        "gold_path": str(gold_path),
        "tesseract_version": version,
        "language": args.language,
        "variants": results,
        "boundary": "Two-page project-authored fixture; transformations are synthetic and do not represent every real scan artifact.",
    }
    (output_path / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    ranked = sorted(results, key=lambda item: item["aggregate"]["cer_all"])
    report = [
        "# TECH-OCR-002-R01 受控退化实验",
        "",
        "> 当前 `SELF-004` 两页样本；退化变体用于发现敏感性，不代表真实扫描件分布。",
        "",
        f"- 输入 SHA-256：`{source_hash}`",
        f"- Tesseract：`{version}`；语言：`{args.language}`；PSM 3；源页渲染 300 DPI。",
        "- 变体：原图、150 DPI 模拟降采样、Gaussian 模糊、低对比度+噪声、额外 3 度旋转。",
        "",
        "| 变体 | 全字符 CER | 中文 CER | 英文/数字 WER | 关键字符串召回 | 平均置信度 | 平均端到端 ms/页 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in ranked:
        aggregate = item["aggregate"]
        report.append(
            f"| {item['variant']} | {aggregate['cer_all']:.4f} | {aggregate['cer_chinese']:.4f} | {aggregate['wer_latin_number']:.4f} | {aggregate['critical_string_recall']:.4f} | {aggregate['mean_word_confidence']:.2f} | {aggregate['elapsed_ms']:.2f} |"
        )
    report.extend(
        [
            "",
            "## 解释边界",
            "",
            f"在本样本上，`{ranked[0]['variant']}` 的全字符 CER 最低，`{ranked[-1]['variant']}` 最高；这是受控变体排序，不是对 OCR 引擎的普遍排名。",
            "任何低质量、印章或手写页都应保留原图和低置信度标记；不能仅凭平均置信度放行问答或引用。",
            "",
        ]
    )
    (output_path / "TECH-OCR-002-R01.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"experiment_id": result["experiment_id"], "output": str(output_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
