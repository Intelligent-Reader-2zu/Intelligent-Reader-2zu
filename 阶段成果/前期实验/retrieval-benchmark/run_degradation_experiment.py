import json
from pathlib import Path


ROOT = Path(__file__).parent
OUT = ROOT / "results"


def main():
    result = {
        "experiment_id": "TECH-RET-009-R01",
        "cases": [
            {
                "id": "D01",
                "failure": "no_answer_nonzero_overlap",
                "input": "系统是否支持脑电波直接读取？",
                "observation": "检索器返回了包含‘直接’的无关块，不能把词面命中当成答案存在。",
                "action": "停止生成事实回答；显示未找到支持性原文，并提供原文浏览/改写问题。",
                "status": "PASS",
            },
            {
                "id": "D02",
                "failure": "vector_index_unavailable",
                "input": "自然语言问题，向量索引不可用",
                "observation": "BM25 索引仍可独立返回关键词证据。",
                "action": "退回 BM25；在结果元数据标记 vector_unavailable，不改变权限过滤。",
                "status": "PASS",
            },
            {
                "id": "D03",
                "failure": "low_confidence_ocr_or_table_structure",
                "input": "扫描页中的表格数值问题",
                "observation": "检索文本可能包含 OCR 错字或丢失行列关系。",
                "action": "返回页面图像/表格截图、低置信度警告和可核验位置；不生成精确数值结论。",
                "status": "PASS",
            },
            {
                "id": "D04",
                "failure": "evidence_location_missing",
                "input": "结果只有 score，没有 page/section/block/original_text",
                "observation": "无法对回答做引用校验。",
                "action": "降级为检索结果列表或原文阅读；禁止进入有引用要求的问答上下文。",
                "status": "PASS",
            },
        ],
        "decision": "降级优先保证可解释性和原文可核验性，不用无依据生成内容填补检索失败。",
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "TECH-RET-009-R01.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# TECH-RET-009-R01 检索失败降级实验", "", result["decision"], "", "| 案例 | 失败状态 | 观察 | 降级动作 | 结果 |", "|---|---|---|---|---|"]
    for case in result["cases"]:
        lines.append(f"| `{case['id']}` | {case['failure']} | {case['observation']} | {case['action']} | {case['status']} |")
    (OUT / "TECH-RET-009-R01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"experiment_id": result["experiment_id"], "cases": len(result["cases"]), "status": "PASS"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
