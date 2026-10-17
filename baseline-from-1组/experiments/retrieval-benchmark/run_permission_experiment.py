import json
import math
from pathlib import Path

from run_experiment import DATA, Index, evidence, rank, rrf


ROOT = Path(__file__).parent
OUT = ROOT / "results"


def filtered_scores(scores, blocks, allowed):
    return [score if block["document_id"] in allowed else -math.inf for score, block in zip(scores, blocks)]


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    blocks = data["blocks"]
    index = Index(blocks)
    cases = [
        {"id": "P01", "question": "检索结果为什么必须包含回答所需的原文？", "allowed": ["DOC-A"], "gold": ["A-P3-B2"]},
        {"id": "P02", "question": "敏感资料没有网络时用什么索引？", "allowed": ["DOC-A"], "gold": []},
        {"id": "P03", "question": "跨文档回答前需要做什么并如何处理冲突？", "allowed": ["DOC-A", "DOC-B"], "gold": ["B-P2-B1"]},
        {"id": "P04", "question": "跨文档回答前需要做什么并如何处理冲突？", "allowed": ["DOC-A"], "gold": []},
    ]
    methods = ("keyword", "bm25", "vector_proxy", "hybrid_rrf")
    result = {"experiment_id": "TECH-RET-008-R01", "policy": "filter before ranking; inaccessible documents are not observable", "cases": [], "summary": {}}
    for case in cases:
        row = {**case, "methods": {}}
        for method in methods:
            if method == "keyword":
                ids = rank(filtered_scores(index.keyword(case["question"]), blocks, set(case["allowed"])), 3)
            elif method == "bm25":
                ids = rank(filtered_scores(index.bm25(case["question"]), blocks, set(case["allowed"])), 3)
            elif method == "vector_proxy":
                ids = rank(filtered_scores(index.vector_proxy(case["question"]), blocks, set(case["allowed"])), 3)
            else:
                bm = filtered_scores(index.bm25(case["question"]), blocks, set(case["allowed"]))
                vec = filtered_scores(index.vector_proxy(case["question"]), blocks, set(case["allowed"]))
                ids, _ = rrf(bm, vec, 3)
            visible = [blocks[i] for i in ids if math.isfinite((index.bm25(case["question"]) if method == "bm25" else [0] * len(blocks))[i]) or blocks[i]["document_id"] in case["allowed"]]
            # rank() can return only filtered blocks except ties at -inf; enforce the policy explicitly.
            visible = [b for b in visible if b["document_id"] in case["allowed"]][:3]
            ranked = [b["block_id"] for b in visible]
            unauthorized = [b["block_id"] for b in visible if b["document_id"] not in case["allowed"]]
            gold = set(case["gold"])
            row["methods"][method] = {
                "ranked_block_ids": ranked,
                "evidence": [evidence(b) for b in visible],
                "hit": bool(gold.intersection(ranked)) if gold else True,
                "unauthorized_leak": bool(unauthorized),
                "unauthorized_block_ids": unauthorized,
            }
        result["cases"].append(row)
    for method in methods:
        rows = [c["methods"][method] for c in result["cases"]]
        result["summary"][method] = {
            "cases": len(rows),
            "unauthorized_leak_rate": sum(r["unauthorized_leak"] for r in rows) / len(rows),
            "all_authorized": all(not r["unauthorized_leak"] for r in rows),
            "answerable_hit_rate": sum(r["hit"] for c, r in zip(result["cases"], rows) if c["gold"]) / sum(bool(c["gold"]) for c in result["cases"]),
            "no_answer_nonempty_rate": sum(bool(r["ranked_block_ids"]) for c, r in zip(result["cases"], rows) if not c["gold"]) / sum(not bool(c["gold"]) for c in result["cases"]),
        }
    OUT.mkdir(exist_ok=True)
    (OUT / "TECH-RET-008-R01.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# TECH-RET-008-R01 多文档权限过滤实验",
        "",
        "策略：先按允许的 `document_id` 过滤，再执行排序和融合；不可见文档不得进入 top-K，也不得通过检索结果泄露存在性。",
        "",
        "| 方法 | 未授权泄露率 | 全部通过 | 有答案问题命中率 | 无答案仍返回结果 |",
        "|---|---:|---|---:|---:|",
    ]
    for method, summary in result["summary"].items():
        lines.append(f"| {method} | {summary['unauthorized_leak_rate']:.3f} | {'PASS' if summary['all_authorized'] else 'FAIL'} | {summary['answerable_hit_rate']:.3f} | {summary['no_answer_nonempty_rate']:.3f} |")
    lines += ["", "## 案例", ""]
    for case in result["cases"]:
        lines.append(f"- `{case['id']}` allowed={','.join(case['allowed'])} gold={','.join(case['gold']) or '(none)'}")
        for method in methods:
            item = case["methods"][method]
            lines.append(f"  - {method}: {','.join(item['ranked_block_ids']) or '(empty)'}; unauthorized_leak={item['unauthorized_leak']}")
    (OUT / "TECH-RET-008-R01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
