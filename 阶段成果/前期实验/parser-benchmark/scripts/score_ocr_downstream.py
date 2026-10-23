from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "results/ocr-tesseract-matrix/result.json"
DEFAULT_DEGRADATION = ROOT / "results/ocr-degradation-matrix/result.json"
DEFAULT_GOLD = ROOT / "samples/self-authored/annotations/SELF-004-ocr-ground-truth.json"
DEFAULT_OUTPUT = ROOT / "results/ocr-downstream"


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text)).lower()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--degradation", type=Path, default=DEFAULT_DEGRADATION)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    gold = json.loads(args.gold.resolve().read_text(encoding="utf-8"))
    expected_pages = {}
    for page in gold["pages"]:
        expected_pages[page["physical_page"]] = set(
            normalize(line) for line in page["lines"]
        )
    queries = gold["critical_strings"]
    records = []
    for source_path in [args.matrix.resolve(), args.degradation.resolve()]:
        source = json.loads(source_path.read_text(encoding="utf-8"))
        if "configurations" in source:
            entries = [(item["config_id"], item["pages"]) for item in source["configurations"]]
        else:
            entries = [(item["variant"], item["pages"]) for item in source["variants"]]
        for name, pages in entries:
            page_text = {page["physical_page"]: normalize(page.get("text", "")) for page in pages}
            query_hits = {}
            for query in queries:
                hits = [page for page, text in page_text.items() if normalize(query) in text]
                expected = [page for page, lines in expected_pages.items() if any(normalize(query) in line for line in lines)]
                query_hits[query] = {
                    "expected_pages": expected,
                    "returned_pages": hits,
                    "page_recall": bool(set(expected).intersection(hits)) if expected else False,
                    "wrong_page_only": bool(hits) and not set(expected).intersection(hits),
                }
            recalls = [item["page_recall"] for item in query_hits.values()]
            wrong_only = [item["wrong_page_only"] for item in query_hits.values()]
            records.append(
                {
                    "source": source["experiment_id"],
                    "configuration": name,
                    "query_page_recall": sum(recalls) / len(recalls),
                    "wrong_page_only_rate": sum(wrong_only) / len(wrong_only),
                    "query_hits": query_hits,
                }
            )
    report = [
        "# TECH-OCR-009-R01 OCR 对检索和引用的影响",
        "",
        "> 使用 `SELF-004` 固定问题集和当前样本金标准；这里只检查关键词对应页是否仍能被召回，不模拟生成式问答。",
        "",
        "| 实验 | 配置/变体 | 查询页召回 | 错页独中率 |",
        "|---|---|---:|---:|",
    ]
    for record in records:
        report.append(
            f"| {record['source']} | {record['configuration']} | {record['query_page_recall']:.4f} | {record['wrong_page_only_rate']:.4f} |"
        )
    report.extend(
        [
            "",
            "## 解释",
            "",
            "OCR 文本即使大部分可读，关键数字、表格词或页码一旦错误，仍可能造成检索漏召回或引用错误。问答链路必须继续检查证据 bbox 和原页，而不能只依据关键词命中。",
            "低置信度或结构不确定时，建议返回页图/裁剪和警告；无可靠证据时拒答。",
            "",
        ]
    )
    (output / "result.json").write_text(json.dumps({"experiment_id": "TECH-OCR-009-R01", "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "TECH-OCR-009-R01.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"experiment_id": "TECH-OCR-009-R01", "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
