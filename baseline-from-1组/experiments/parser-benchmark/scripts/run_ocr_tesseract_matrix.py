from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
import unicodedata
from pathlib import Path

import cv2
import fitz


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "samples/self-authored/pdf/SELF-004-scanned.pdf"
DEFAULT_GOLD = ROOT / "samples/self-authored/annotations/SELF-004-ocr-ground-truth.json"
DEFAULT_OUTPUT = ROOT / "results/ocr-tesseract-matrix"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def edit_distance(reference: list[str] | str, hypothesis: list[str] | str) -> int:
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


def normalize_cer(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def latin_number_tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    return re.findall(r"[a-z]+(?:-[a-z0-9]+)*|\d+(?:\.\d+)?", normalized)


def chinese_characters(text: str) -> str:
    return "".join(re.findall(r"[\u3400-\u9fff]", unicodedata.normalize("NFKC", text)))


def rate(reference: list[str] | str, hypothesis: list[str] | str) -> float | None:
    if not reference:
        return None
    return edit_distance(reference, hypothesis) / len(reference)


def preprocess(image_path: Path, mode: str) -> Path:
    if mode == "none":
        return image_path
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError(f"cannot read rendered page: {image_path}")
    if mode == "otsu":
        output = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    else:
        raise ValueError(f"unsupported preprocessing mode: {mode}")
    processed_path = image_path.with_name(image_path.stem + f"-{mode}.png")
    if not cv2.imwrite(str(processed_path), output):
        raise RuntimeError(f"cannot write preprocessed page: {processed_path}")
    return processed_path


def run_tesseract(image_path: Path, language: str, psm: int) -> tuple[str, list[dict], float, str]:
    command = [
        "tesseract",
        str(image_path),
        "stdout",
        "-l",
        language,
        "--psm",
        str(psm),
        "tsv",
    ]
    started = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, check=False)
    elapsed_ms = (time.perf_counter() - started) * 1000
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(f"Tesseract failed ({completed.returncode}): {stderr.strip()}")

    words = []
    columns = [
        "level",
        "page_num",
        "block_num",
        "par_num",
        "line_num",
        "word_num",
        "left",
        "top",
        "width",
        "height",
        "conf",
        "text",
    ]
    for line in stdout.splitlines()[1:]:
        parts = line.split("\t", len(columns) - 1)
        if len(parts) != len(columns):
            continue
        row = dict(zip(columns, parts, strict=True))
        text = (row.get("text") or "").strip()
        if not text:
            continue
        confidence = float(row["conf"])
        if confidence < 0:
            continue
        words.append(
            {
                "text": text,
                "confidence": confidence,
                "bbox": [int(row["left"]), int(row["top"]), int(row["width"]), int(row["height"])],
                "block": int(row["block_num"]),
                "paragraph": int(row["par_num"]),
                "line": int(row["line_num"]),
                "word": int(row["word_num"]),
            }
        )

    grouped: dict[tuple[int, int, int], list[dict]] = {}
    for word in words:
        key = (word["block"], word["paragraph"], word["line"])
        grouped.setdefault(key, []).append(word)
    lines = [" ".join(item["text"] for item in line_words) for line_words in grouped.values()]
    return "\n".join(lines), words, elapsed_ms, stderr


def score_page(reference: str, hypothesis: str, critical_strings: list[str], words: list[dict]) -> dict:
    ref_cer = normalize_cer(reference)
    hyp_cer = normalize_cer(hypothesis)
    ref_zh = chinese_characters(reference)
    hyp_zh = chinese_characters(hypothesis)
    ref_tokens = latin_number_tokens(reference)
    hyp_tokens = latin_number_tokens(hypothesis)
    normalized_hypothesis = normalize_cer(hypothesis).lower()
    keyword_hits = {
        item: normalize_cer(item).lower() in normalized_hypothesis
        for item in critical_strings
    }
    confidences = [item["confidence"] for item in words]
    return {
        "cer_all": rate(ref_cer, hyp_cer),
        "cer_chinese": rate(ref_zh, hyp_zh),
        "wer_latin_number": rate(ref_tokens, hyp_tokens),
        "critical_string_recall": sum(keyword_hits.values()) / len(keyword_hits),
        "critical_string_hits": keyword_hits,
        "word_count": len(words),
        "mean_word_confidence": sum(confidences) / len(confidences) if confidences else None,
        "low_confidence_word_ratio": (
            sum(value < 60 for value in confidences) / len(confidences) if confidences else None
        ),
        "words_with_bbox_ratio": (
            sum(all(value >= 0 for value in item["bbox"]) for item in words) / len(words) if words else None
        ),
    }


def aggregate(configuration: dict) -> dict:
    pages = configuration["pages"]
    keys = [
        "cer_all",
        "cer_chinese",
        "wer_latin_number",
        "critical_string_recall",
        "mean_word_confidence",
        "low_confidence_word_ratio",
        "words_with_bbox_ratio",
        "render_ms",
        "preprocess_ms",
        "ocr_ms",
        "elapsed_ms",
    ]
    result = {}
    for key in keys:
        values = [page[key] for page in pages if page.get(key) is not None]
        result[key] = sum(values) / len(values) if values else None
    result["page_success_rate"] = sum(page["status"] == "succeeded" for page in pages) / len(pages)
    return result


def write_report(result: dict, path: Path) -> None:
    ranked = sorted(
        result["configurations"],
        key=lambda item: (
            item["aggregate"]["cer_all"],
            item["aggregate"]["elapsed_ms"],
        ),
    )
    lines = [
        "# TECH-OCR-001-R01 Tesseract OCR 配置矩阵",
        "",
        "> 这是当前 `SELF-004` 版本上的受控基线，不代表真实扫描件总体质量或最终选型。",
        "",
        "## 运行范围",
        "",
        f"- 输入 SHA-256：`{result['source_sha256']}`",
        f"- Tesseract：`{result['tesseract_version']}`；语言：`{result['language']}`",
        "- 指标：去空白全字符 CER、中文字符 CER、英文/数字 WER、关键字符串召回、词 bbox、OCR 时延和端到端页时延。",
        "- 未覆盖：印章、手写、双栏、复杂表格结构、公式和云服务。",
        "",
        "## 配置结果",
        "",
        "| 配置 | 全字符 CER | 中文 CER | 英文/数字 WER | 关键字符串召回 | 平均置信度 | 低置信词比例 | OCR ms/页 | 端到端 ms/页 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in ranked:
        aggregate_result = item["aggregate"]
        lines.append(
            "| {id} | {cer:.4f} | {zh:.4f} | {wer:.4f} | {recall:.4f} | {conf:.2f} | {low:.4f} | {ocr:.2f} | {elapsed:.2f} |".format(
                id=item["config_id"],
                cer=aggregate_result["cer_all"],
                zh=aggregate_result["cer_chinese"],
                wer=aggregate_result["wer_latin_number"],
                recall=aggregate_result["critical_string_recall"],
                conf=aggregate_result["mean_word_confidence"],
                low=aggregate_result["low_confidence_word_ratio"],
                ocr=aggregate_result["ocr_ms"],
                elapsed=aggregate_result["elapsed_ms"],
            )
        )
    best = ranked[0]
    lines.extend(
        [
            "",
            "## 阶段性解释",
            "",
            f"按本实验的全字符 CER 排序，`{best['config_id']}` 最低；它只是在两页自制样本上的候选配置，不能外推到真实扫描件。",
            "置信度只用于观察校准，不能代替 CER/WER。表格字符串命中也不等于恢复了行列或单元格结构。",
            "第二页带 1.4 度倾斜，应结合逐页结果判断配置是否对倾斜敏感。",
            "",
            "## 下一步",
            "",
            "1. 增加印章、手写、低分辨率和模糊变体，执行 `TECH-OCR-002/003`。",
            "2. 将双栏和表格/公式样本渲染为图像，执行阅读顺序和结构评分。",
            "3. 让 Docling、PaddleOCR/PP-Structure 等候选重跑相同输入哈希后再横向比较。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


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
        raise SystemExit(
            f"source hash mismatch: expected {gold['source_sha256']}, actual {source_hash}"
        )

    version = subprocess.run(
        ["tesseract", "--version"], capture_output=True, check=True, text=True, encoding="utf-8"
    ).stdout.splitlines()[0]
    configurations = [
        {"dpi": 144, "psm": 3, "preprocess": "none"},
        {"dpi": 144, "psm": 3, "preprocess": "otsu"},
        {"dpi": 300, "psm": 3, "preprocess": "none"},
        {"dpi": 300, "psm": 3, "preprocess": "otsu"},
        {"dpi": 300, "psm": 6, "preprocess": "none"},
        {"dpi": 300, "psm": 6, "preprocess": "otsu"},
    ]
    document = fitz.open(pdf_path)
    results = []
    for config in configurations:
        config_id = f"dpi{config['dpi']}-psm{config['psm']}-{config['preprocess']}"
        config_dir = output_path / config_id
        config_dir.mkdir(parents=True, exist_ok=True)
        page_results = []
        for page_index, (page, reference_page) in enumerate(zip(document, gold["pages"], strict=True), 1):
            page_started = time.perf_counter()
            image_path = config_dir / f"page-{page_index}.png"
            render_started = time.perf_counter()
            pixmap = page.get_pixmap(dpi=config["dpi"], alpha=False)
            pixmap.save(image_path)
            render_ms = (time.perf_counter() - render_started) * 1000
            preprocess_started = time.perf_counter()
            ocr_image_path = preprocess(image_path, config["preprocess"])
            preprocess_ms = (time.perf_counter() - preprocess_started) * 1000
            reference = "\n".join(reference_page["lines"])
            try:
                text, words, ocr_ms, stderr = run_tesseract(
                    ocr_image_path, args.language, config["psm"]
                )
                metrics = score_page(reference, text, gold["critical_strings"], words)
                page_result = {
                    "physical_page": page_index,
                    "status": "succeeded",
                    "render_size": [pixmap.width, pixmap.height],
                    "render_ms": render_ms,
                    "preprocess_ms": preprocess_ms,
                    "ocr_ms": ocr_ms,
                    "elapsed_ms": (time.perf_counter() - page_started) * 1000,
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
                    "render_ms": render_ms,
                    "preprocess_ms": preprocess_ms,
                    "ocr_ms": None,
                    "elapsed_ms": (time.perf_counter() - page_started) * 1000,
                }
            page_results.append(page_result)
            (config_dir / f"page-{page_index}.json").write_text(
                json.dumps(page_result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        config_result = {"config_id": config_id, **config, "pages": page_results}
        config_result["aggregate"] = aggregate(config_result)
        results.append(config_result)

    result = {
        "experiment_id": "TECH-OCR-001-R01",
        "source_path": str(pdf_path),
        "source_sha256": source_hash,
        "gold_path": str(gold_path),
        "tesseract_version": version,
        "language": args.language,
        "configurations": results,
        "boundary": "Two-page project-authored fixture only; not representative of real scans.",
    }
    (output_path / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(result, output_path / "TECH-OCR-001-R01.md")
    print(json.dumps({"experiment_id": result["experiment_id"], "output": str(output_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
