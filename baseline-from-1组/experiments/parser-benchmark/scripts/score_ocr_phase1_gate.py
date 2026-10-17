from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/ocr-phase1-gate"
MATRIX = ROOT / "results/ocr-tesseract-matrix/result.json"
TESS_DEGRADATION = ROOT / "results/ocr-degradation-matrix/result.json"
RAPID = ROOT / "results/ocr-rapidocr/result.json"
RAPID_DEGRADATION = ROOT / "results/ocr-rapidocr-degradation/result.json"
PADDLE = ROOT / "results/ocr-paddleocr/result-R02.json"

QUERIES = [
    {"id": "Q01", "text": "OCR TEST", "expected_pages": [1, 2]},
    {"id": "Q02", "text": "English abbreviation", "expected_pages": [1, 2]},
    {"id": "Q03", "text": "12345", "expected_pages": [1, 2]},
    {"id": "Q04", "text": "物理页码", "expected_pages": [1, 2]},
    {"id": "Q05", "text": "表格区域", "expected_pages": [1, 2]},
    {"id": "Q06", "text": "A-01 0.95", "expected_pages": [1, 2]},
    {"id": "Q07", "text": "表格候选单元格", "expected_pages": [1, 2]},
    {"id": "Q08", "text": "page label: 1", "expected_pages": [1]},
    {"id": "Q09", "text": "page label: 2", "expected_pages": [2]},
    {"id": "Q10", "text": "第 1 页 文档解析质量验证", "expected_pages": [1]},
    {"id": "Q11", "text": "第 2 页 文档解析质量验证", "expected_pages": [2]},
]
NEGATIVE_QUERIES = ["X-99", "不存在的审批结论"]
GATES = {
    "page_success_rate_min": 1.0,
    "cer_all_max": 0.05,
    "cer_chinese_max": 0.03,
    "wer_latin_number_max": 0.10,
    "query_expected_page_recall_min": 1.0,
    "citation_line_bbox_coverage_min": 1.0,
    "wrong_page_hit_count_max": 0,
    "negative_query_hit_count_max": 0,
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text)).lower()


def union_bbox(boxes: list[list[float]]) -> list[float]:
    xs = [box[0] for box in boxes]
    ys = [box[1] for box in boxes]
    rights = [box[0] + box[2] for box in boxes]
    bottoms = [box[1] + box[3] for box in boxes]
    return [min(xs), min(ys), max(rights) - min(xs), max(bottoms) - min(ys)]


def tesseract_lines(page: dict) -> list[dict]:
    grouped: dict[tuple[int, int, int], list[dict]] = {}
    for word in page.get("words", []):
        key = (word["block"], word["paragraph"], word["line"])
        grouped.setdefault(key, []).append(word)
    return [
        {
            "text": " ".join(word["text"] for word in words),
            "bbox": union_bbox([word["bbox"] for word in words]),
        }
        for words in grouped.values()
    ]


def rapid_lines(page: dict) -> list[dict]:
    return [{"text": item["text"], "bbox": item["bbox"]} for item in page.get("items", [])]


def paddle_lines(page: dict) -> list[dict]:
    return [{"text": row["text"], "bbox": row["bbox"]} for row in page.get("rows", [])]


def evaluate_queries(pages: list[dict], line_adapter) -> dict:
    page_text = {
        page["physical_page"]: normalize(page.get("text", ""))
        for page in pages
        if page.get("status") == "succeeded"
    }
    page_lines = {
        page["physical_page"]: line_adapter(page)
        for page in pages
        if page.get("status") == "succeeded"
    }
    records = []
    expected_pair_count = 0
    expected_hit_count = 0
    located_pair_count = 0
    wrong_page_hits = 0
    all_pages = set(page_text)
    for query in QUERIES:
        needle = normalize(query["text"])
        expected = set(query["expected_pages"])
        hits = {page_no for page_no, text in page_text.items() if needle in text}
        located = {
            page_no
            for page_no, lines in page_lines.items()
            if any(needle in normalize(line["text"]) and line.get("bbox") for line in lines)
        }
        expected_pair_count += len(expected)
        expected_hit_count += len(expected & hits)
        located_pair_count += len(expected & located)
        wrong_page_hits += len(hits & (all_pages - expected))
        records.append(
            {
                **query,
                "returned_pages": sorted(hits),
                "located_pages": sorted(located),
            }
        )
    negative_hits = {
        query: sorted(page_no for page_no, text in page_text.items() if normalize(query) in text)
        for query in NEGATIVE_QUERIES
    }
    return {
        "query_expected_page_recall": expected_hit_count / expected_pair_count,
        "citation_line_bbox_coverage": located_pair_count / expected_pair_count,
        "wrong_page_hit_count": wrong_page_hits,
        "negative_query_hit_count": sum(len(hits) for hits in negative_hits.values()),
        "queries": records,
        "negative_queries": negative_hits,
    }


def check_gate(record: dict) -> dict:
    checks = {
        "page_success_rate": record["page_success_rate"] >= GATES["page_success_rate_min"],
        "cer_all": record["cer_all"] <= GATES["cer_all_max"],
        "cer_chinese": record["cer_chinese"] <= GATES["cer_chinese_max"],
        "wer_latin_number": record["wer_latin_number"] <= GATES["wer_latin_number_max"],
        "query_expected_page_recall": record["query_expected_page_recall"]
        >= GATES["query_expected_page_recall_min"],
        "citation_line_bbox_coverage": record["citation_line_bbox_coverage"]
        >= GATES["citation_line_bbox_coverage_min"],
        "wrong_page_hit_count": record["wrong_page_hit_count"]
        <= GATES["wrong_page_hit_count_max"],
        "negative_query_hit_count": record["negative_query_hit_count"]
        <= GATES["negative_query_hit_count_max"],
    }
    return {"passed": all(checks.values()), "checks": checks}


def config(source: dict, config_id: str) -> dict:
    return next(item for item in source["configurations"] if item["config_id"] == config_id)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    rapid = json.loads(RAPID.read_text(encoding="utf-8"))
    paddle = json.loads(PADDLE.read_text(encoding="utf-8"))
    tess_deg = json.loads(TESS_DEGRADATION.read_text(encoding="utf-8"))
    rapid_deg = json.loads(RAPID_DEGRADATION.read_text(encoding="utf-8"))

    sources = [
        ("Tesseract", "dpi144-psm3-none", config(matrix, "dpi144-psm3-none"), tesseract_lines, "end_to_end_mean"),
        ("Tesseract", "dpi300-psm3-none", config(matrix, "dpi300-psm3-none"), tesseract_lines, "end_to_end_mean"),
        ("RapidOCR", "dpi144", config(rapid, "dpi144"), rapid_lines, "ocr_only_mean"),
        ("RapidOCR", "dpi300", config(rapid, "dpi300"), rapid_lines, "ocr_only_mean"),
        ("PaddleOCR", "dpi144", config(paddle, "dpi144"), paddle_lines, "ocr_only_p95"),
        ("PaddleOCR", "dpi300", config(paddle, "dpi300"), paddle_lines, "ocr_only_p95"),
    ]
    candidates = []
    for engine, config_id, source, adapter, timing_scope in sources:
        aggregate = source["aggregate"]
        query_metrics = evaluate_queries(source["pages"], adapter)
        timing_ms = (
            aggregate.get("elapsed_ms")
            or aggregate.get("ocr_ms")
            or aggregate.get("elapsed_ms_p95")
        )
        if timing_scope == "ocr_only_p95":
            timing_ms = aggregate["elapsed_ms_p95"]
        record = {
            "engine": engine,
            "configuration": config_id,
            "page_success_rate": aggregate["page_success_rate"],
            "cer_all": aggregate["cer_all"],
            "cer_chinese": aggregate["cer_chinese"],
            "wer_latin_number": aggregate["wer_latin_number"],
            "critical_string_recall": aggregate["critical_string_recall"],
            "timing_ms": timing_ms,
            "timing_scope": timing_scope,
            **query_metrics,
        }
        record["gate"] = check_gate(record)
        candidates.append(record)

    degradation = []
    for engine, source in (("Tesseract", tess_deg), ("RapidOCR", rapid_deg)):
        for variant in source["variants"]:
            aggregate = variant["aggregate"]
            checks = {
                "page_success_rate": aggregate["page_success_rate"] >= 1.0,
                "cer_all": aggregate["cer_all"] <= GATES["cer_all_max"],
                "cer_chinese": aggregate["cer_chinese"] <= GATES["cer_chinese_max"],
                "wer_latin_number": aggregate["wer_latin_number"] <= GATES["wer_latin_number_max"],
                "critical_string_recall": aggregate["critical_string_recall"] >= 1.0,
            }
            degradation.append(
                {
                    "engine": engine,
                    "variant": variant["variant"],
                    "cer_all": aggregate["cer_all"],
                    "cer_chinese": aggregate["cer_chinese"],
                    "wer_latin_number": aggregate["wer_latin_number"],
                    "critical_string_recall": aggregate["critical_string_recall"],
                    "timing_ms": aggregate.get("elapsed_ms") or aggregate.get("ocr_ms"),
                    "timing_scope": "end_to_end" if engine == "Tesseract" else "ocr_only",
                    "gate": {"passed": all(checks.values()), "checks": checks},
                }
            )

    result = {
        "experiment_id": "TECH-OCR-022-R01",
        "source_sha256": matrix["source_sha256"],
        "provisional_gates": GATES,
        "queries": QUERIES,
        "negative_queries": NEGATIVE_QUERIES,
        "candidates": candidates,
        "degradation": degradation,
        "decision": {
            "primary_candidate": "RapidOCR dpi144",
            "fallback_candidate": "Tesseract dpi300-psm3-none",
            "layout_enhancement": "disabled by default; PP-StructureV3 asynchronous experiment only",
            "scope": "Clear, near-upright printed single-column scans only; all other scans are best-effort with original-page review.",
        },
        "boundary": "Provisional phase-one gate derived from a two-page project-authored fixture and synthetic degradations; not a production acceptance threshold.",
    }
    (OUT / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# TECH-OCR-022-R01 一期 OCR 候选门槛与回退决策",
        "",
        "> 本报告把现有本地实验放到同一组暂定门槛下。样本只有两页，结论是一期实现候选，不是生产验收或最终选型。",
        "",
        "## 暂定门槛",
        "",
        "清晰印刷页要求：页面成功率 100%、全字符 CER <= 5%、中文 CER <= 3%、英文/数字 WER <= 10%、11 个固定查询的预期页召回和行 bbox 定位均为 100%，且没有错页或两个负查询的误命中。时延因各脚本统计范围不同，仅展示，不参与本轮通过判定。",
        "",
        "| 引擎 | 配置 | CER | 中文 CER | 英/数 WER | 查询预期页召回 | 引用行 bbox | 时延 ms | 统计范围 | 结果 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for item in candidates:
        lines.append(
            f"| {item['engine']} | {item['configuration']} | {item['cer_all']:.4f} | "
            f"{item['cer_chinese']:.4f} | {item['wer_latin_number']:.4f} | "
            f"{item['query_expected_page_recall']:.4f} | {item['citation_line_bbox_coverage']:.4f} | "
            f"{item['timing_ms']:.2f} | {item['timing_scope']} | "
            f"{'通过' if item['gate']['passed'] else '不通过'} |"
        )
    lines.extend(
        [
            "",
            "## 退化页结论",
            "",
            "Tesseract 与 RapidOCR 在五组退化页中均没有一个引擎满足所有暂定质量门槛。RapidOCR 的关键字符串召回全部为 1.0，但部分页面 CER 达 8.73%、英文/数字 WER 达 16.67%；这证明关键词可命中不能替代准确文本和精确编号验收。",
            "",
            "## 一期建议",
            "",
            "1. 主候选采用 RapidOCR 144 DPI：清晰页在本样本通过字符、英文数字、查询和 bbox 门槛，依赖为本地 ONNX Runtime。",
            "2. Tesseract 300 DPI 作为第二本地引擎重试：它的字符指标通过，但 `A-01 0.95` 在第一页未被精确查询定位，整体门槛不通过；当前端到端均值约 5.06 秒/页。不得把两个引擎文本静默拼接，重试后仍须重新门控或降级。",
            "3. PaddleOCR 2.10 虽然热运行较快且中文字符正确，但英文/数字 WER 41.67%-50%，不承担一期精确编号主路径。",
            "4. PP-StructureV3 默认关闭，只保留异步实验入口。表格、双栏、公式、印章和手写统一标记结构不确定并展示原页。",
            "5. 一期不承诺轻度退化必然准确。模糊、降采样、噪声和额外旋转均进入 `ocr_low_confidence` 或人工复核；关键数字、日期、编号不得仅凭 OCR 自动作答。",
            "",
            "## 仍需放行条件",
            "",
            "- 至少补足任务书要求的 5 份扫描 PDF，并覆盖真实清晰扫描、倾斜、低清、印章或手写标记。",
            "- 用真实样本重新确定阈值；本报告的 5%/3%/10% 仅为当前样本上的工程门槛。",
            "- 实现页级状态、原页回看、双引擎重试和失败不入精确问答的最小链路后，再把扫描 PDF 从实验能力转为一期功能。",
            "",
        ]
    )
    (OUT / "TECH-OCR-022-R01.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"experiment_id": result["experiment_id"], "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
