import json
import re
from pathlib import Path


ROOT = Path(__file__).parent
PARSER_ROOT = ROOT.parent / "parser-benchmark"
IR_ROOT = PARSER_ROOT / "results" / "text-structure" / "ir"
ANN_ROOT = PARSER_ROOT / "samples" / "self-authored" / "annotations"
OUT = ROOT / "results"


def terms(text):
    return re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9][a-zA-Z0-9_@./-]*", text.lower())


def score(text, query):
    body = set(terms(text))
    q = set(terms(query))
    return sum(t in body for t in q) / max(1, len(q))


def as_block(doc, element):
    return {
        "document_id": doc["doc_id"],
        "document_version": doc.get("config_hash"),
        "source_hash": doc.get("source_hash"),
        "block_id": element["element_id"],
        "page": element.get("physical_page"),
        "printed_page_label": element.get("printed_page_label"),
        "section_path": element.get("heading_path") or [],
        "paragraph": element.get("reading_order_index"),
        "char_start": element.get("char_start"),
        "char_end": element.get("char_end"),
        "bbox": element.get("bbox"),
        "block_type": element.get("element_type"),
        "text": element.get("text", ""),
        "warnings": doc.get("warnings", []),
    }


def main():
    samples = ["SELF-001", "SELF-002", "SELF-003", "SELF-005", "SELF-008"]
    blocks = []
    sample_results = []
    for sample in samples:
        ir_path = IR_ROOT / f"{sample}.json"
        ann_path = ANN_ROOT / f"{sample}.json"
        if not ir_path.exists() or not ann_path.exists():
            continue
        doc = json.loads(ir_path.read_text(encoding="utf-8"))
        ann = json.loads(ann_path.read_text(encoding="utf-8"))
        doc_blocks = [as_block(doc, element) for element in doc.get("elements", []) if element.get("text")]
        blocks.extend(doc_blocks)
        for fragment in ann.get("expected_evidence_fragments", []):
            gold = [b["block_id"] for b in doc_blocks if fragment.lower() in b["text"].lower()]
            ranked = sorted(doc_blocks, key=lambda b: (-score(b["text"], fragment), b["block_id"]))[:3]
            ranked_ids = [b["block_id"] for b in ranked if score(b["text"], fragment) > 0]
            hit = bool(set(gold).intersection(ranked_ids))
            evidence = [b for b in ranked if b["block_id"] in ranked_ids]
            sample_results.append({
                "sample_id": sample,
                "query": fragment,
                "gold_block_ids": gold,
                "ranked_block_ids": ranked_ids,
                "hit": hit,
                "evidence": evidence,
            })
    checked = sum(1 for row in sample_results for item in row["evidence"])
    complete = sum(1 for row in sample_results for item in row["evidence"] if all(item.get(k) not in (None, "") for k in ("document_id", "source_hash", "block_id", "page", "char_start", "char_end", "bbox", "text")))
    result = {
        "experiment_id": "TECH-RET-010-R01",
        "samples": samples,
        "documents_loaded": sorted(set(b["document_id"] for b in blocks)),
        "blocks_loaded": len(blocks),
        "queries": sample_results,
        "query_count": len(sample_results),
        "hit_rate_at_3": round(sum(row["hit"] for row in sample_results) / max(1, len(sample_results)), 3),
        "evidence_metadata_completeness": round(complete / max(1, checked), 3),
        "scope": "real parser IR retrieval; keyword evidence-chain check, not vector quality",
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "TECH-RET-010-R01.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# TECH-RET-010-R01 真实解析 IR 检索与证据回溯",
        "",
        f"样本：{', '.join(samples)}；载入文档：{len(result['documents_loaded'])}；块数：{result['blocks_loaded']}；问题数：{result['query_count']}。",
        "",
        f"固定片段 Hit@3：**{result['hit_rate_at_3']:.3f}**；返回证据元数据完整率：**{result['evidence_metadata_completeness']:.3f}**。",
        "",
        "该实验直接读取已有 PyMuPDF/Markdown 等解析 IR，验证检索结果能否带回源哈希、物理页码、bbox、字符偏移和原文；它不代表向量检索质量，也不替代人工阅读顺序/标题结构验收。",
        "",
        "| 样本 | 查询片段 | Gold | Top-3 | 命中 | 页码/bbox/字符偏移可回溯 |",
        "|---|---|---|---|---|---|",
    ]
    for row in sample_results:
        metadata_ok = all(all(item.get(k) not in (None, "") for k in ("source_hash", "page", "char_start", "char_end", "bbox")) for item in row["evidence"])
        lines.append(f"| {row['sample_id']} | {row['query']} | {','.join(row['gold_block_ids']) or '(none)'} | {','.join(row['ranked_block_ids']) or '(none)'} | {'YES' if row['hit'] else 'NO'} | {'YES' if metadata_ok else 'NO'} |")
    (OUT / "TECH-RET-010-R01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"experiment_id": result["experiment_id"], "query_count": result["query_count"], "hit_rate_at_3": result["hit_rate_at_3"], "evidence_metadata_completeness": result["evidence_metadata_completeness"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
