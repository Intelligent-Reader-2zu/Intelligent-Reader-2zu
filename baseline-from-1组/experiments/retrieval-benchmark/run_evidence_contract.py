import json
from pathlib import Path


ROOT = Path(__file__).parent
RESULT = ROOT / "results" / "TECH-RET-001-R01.json"
OUT = ROOT / "results"

REQUIRED = ("document_id", "document_version", "source_hash", "block_id", "page", "section_path", "paragraph", "char_start", "char_end", "text")


def main():
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    checked = 0
    complete = 0
    failures = []
    for query in data["queries"]:
        for method, method_result in query["methods"].items():
            for item in method_result["evidence"]:
                checked += 1
                missing = [key for key in REQUIRED if item.get(key) in (None, "")]
                if not missing:
                    complete += 1
                elif len(failures) < 12:
                    failures.append({"query_id": query["id"], "method": method, "block_id": item.get("block_id"), "missing": missing})
    output = {
        "experiment_id": "TECH-RET-007-R01",
        "required_fields": list(REQUIRED),
        "checked_evidence": checked,
        "complete_evidence": complete,
        "completeness": round(complete / checked, 3) if checked else 0.0,
        "failures_sample": failures,
        "interpretation": "当前合成检索结果保留页码/章节/段落/原文，但未提供版本、源哈希和字符偏移；字段已显式返回 null，不能宣称引用链路完整。",
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "TECH-RET-007-R01.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# TECH-RET-007-R01 证据定位契约检查",
        "",
        f"检查证据数：{checked}；完整证据数：{complete}；完整率：{output['completeness']:.3f}。",
        "",
        "当前结果明确保留 `document_id`、`block_id`、页码、章节、段落和原文；版本、源哈希、字符偏移等缺失字段以 `null` 返回，不能把页码命中误写成完整引用链路。",
        "",
        "## 必需字段",
        "",
        "`" + "`, `".join(REQUIRED) + "`",
        "",
        "## 样例缺失",
        "",
    ]
    for failure in failures:
        lines.append(f"- `{failure['query_id']}` / `{failure['method']}` / `{failure['block_id']}`：缺少 {', '.join(failure['missing'])}")
    (OUT / "TECH-RET-007-R01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"experiment_id": output["experiment_id"], "checked": checked, "completeness": output["completeness"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
