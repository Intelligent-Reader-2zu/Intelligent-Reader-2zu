"""Run retrieval checks that depend on the existing parser/OCR artifacts.

This deliberately does not manufacture a vector score.  It measures whether
OCR text, table-like text, and multi-column evidence can be found and traced
back to the source artifact.
"""
import json
import re
from pathlib import Path


ROOT = Path(__file__).parent
PARSER = ROOT.parent / "parser-benchmark"
OUT = ROOT / "results"


def terms(text):
    return re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9][A-Za-z0-9_.@/-]*", text.lower())


def score(text, query):
    body = set(terms(text))
    wanted = set(terms(query))
    return sum(token in body for token in wanted) / max(1, len(wanted))


def ocr_blocks():
    blocks = []
    root = PARSER / "results" / "ocr-baseline"
    for page in (1, 2):
        path = root / f"SELF-004-p{page}.txt.txt"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        blocks.append({
            "document_id": "SELF-004",
            "source_hash": "ab008a1879ed22c5f92abe0dab30f1bbd2ffe2e462b1b2c25ec55cc7fa03fa63",
            "block_id": f"SELF-004-p{page}-ocr",
            "page": page,
            "section_path": ["OCR page"],
            "paragraph": 1,
            "text": text,
            "block_type": "ocr_page",
        })
    return blocks


def structured_blocks():
    root = PARSER / "results" / "text-structure" / "ir"
    output = []
    for sample in ("SELF-002", "SELF-003", "SELF-005", "SELF-008"):
        path = root / f"{sample}.json"
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        for element in doc.get("elements", []):
            if not element.get("text"):
                continue
            output.append({
                "document_id": doc.get("doc_id", sample),
                "source_hash": doc.get("source_hash"),
                "block_id": element.get("element_id"),
                "page": element.get("physical_page"),
                "section_path": element.get("heading_path") or [],
                "paragraph": element.get("reading_order_index"),
                "char_start": element.get("char_start"),
                "char_end": element.get("char_end"),
                "bbox": element.get("bbox"),
                "text": element.get("text", ""),
                "block_type": element.get("element_type"),
            })
    return output


def run_case(case_id, query, gold_pages, blocks, kind):
    ranked = sorted(blocks, key=lambda b: (-score(b["text"], query), b["block_id"]))
    ranked = [b for b in ranked if score(b["text"], query) > 0][:3]
    pages = sorted({b.get("page") for b in ranked if b.get("page") is not None})
    hit = bool(set(pages).intersection(gold_pages))
    return {
        "id": case_id,
        "kind": kind,
        "query": query,
        "gold_pages": sorted(gold_pages),
        "ranked_block_ids": [b["block_id"] for b in ranked],
        "returned_pages": pages,
        "hit_at_3": hit,
        "evidence_has_original_text": all(bool(b.get("text")) for b in ranked),
        "evidence_has_page": all(b.get("page") is not None for b in ranked),
        "evidence": ranked,
    }


def main():
    ocr = ocr_blocks()
    structured = structured_blocks()
    cases = []
    for case_id, query in enumerate(("OCR TEST", "12345", "物理页码", "A-01", "表格候选单元格"), 1):
        cases.append(run_case(f"OCR-{case_id:02d}", query, {1, 2}, ocr, "ocr"))
    # These queries intentionally target table/citation and reading-order evidence.
    for case_id, query in enumerate(("Recall@k", "physical_page", "heading_path", "参考文献"), 1):
        cases.append(run_case(f"IR-{case_id:02d}", query, {1}, structured, "structured_ir"))
    result = {
        "experiment_id": "TECH-RET-011-R01",
        "artifacts": {
            "ocr": "ocr-baseline/SELF-004-p{1,2}.txt.txt",
            "structured_ir_samples": ["SELF-002", "SELF-003", "SELF-005", "SELF-008"],
        },
        "ocr_page_recall_at_3": round(sum(c["hit_at_3"] for c in cases if c["kind"] == "ocr") / 5, 3),
        "structured_ir_hit_at_3": round(sum(c["hit_at_3"] for c in cases if c["kind"] == "structured_ir") / 4, 3),
        "ocr_evidence_page_rate": round(sum(c["evidence_has_page"] for c in cases if c["kind"] == "ocr") / 5, 3),
        "cases": cases,
        "boundary": "Keyword/OCR and parser-IR traceability only; no embedding quality claim.",
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "TECH-RET-011-R01.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# TECH-RET-011-R01 OCR 与结构 IR 检索下游验证", "",
        f"OCR 固定查询页命中率 Hit@3：**{result['ocr_page_recall_at_3']:.3f}**；结构 IR Hit@3：**{result['structured_ir_hit_at_3']:.3f}**；OCR 证据页码携带率：**{result['ocr_evidence_page_rate']:.3f}**。", "",
        "该实验复用现有 Tesseract OCR 文本和解析 IR，验证中文、英文、数字、表格候选词能否回到物理页。它不替代 CER/WER，也不代表真实向量检索质量；OCR 文本中的字符错误仍需原页核验。", "",
        "| 用例 | 类型 | 查询 | 返回页 | 命中 | 原文 | 页码 |", "|---|---|---|---|---|---|---|",
    ]
    for c in cases:
        lines.append(f"| {c['id']} | {c['kind']} | {c['query']} | {','.join(map(str, c['returned_pages'])) or '-'} | {'YES' if c['hit_at_3'] else 'NO'} | {'YES' if c['evidence_has_original_text'] else 'NO'} | {'YES' if c['evidence_has_page'] else 'NO'} |")
    (OUT / "TECH-RET-011-R01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("experiment_id", "ocr_page_recall_at_3", "structured_ir_hit_at_3", "ocr_evidence_page_rate")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
