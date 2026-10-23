"""Run the complete fixed QA set as small batches through official Codex CLI."""

from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path

from run_codex_cli_batch_qa import evaluate
from run_minimal_qa import fixture


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"


def aggregate(model: str, parts: list[dict]) -> dict:
    rows = [row for part in parts for row in part["rows"]]
    completed = [row for row in rows if row["error"] is None and row["json_valid"]]
    review = [row for row in completed if row["expected_status"] != "answered"]
    timings = [part["latency_ms"]["p50"] for part in parts if part["latency_ms"]["p50"] is not None]
    return {
        "provider": "codex_official_cli_grouped",
        "model": model,
        "query_count": len(rows),
        "completed_query_count": len(completed),
        "transport_error_count": len(rows) - len(completed),
        "status_accuracy": round(statistics.mean(row["status_correct"] for row in completed), 3) if completed else None,
        "json_valid_rate": round(statistics.mean(row["json_valid"] for row in rows), 3) if rows else None,
        "citation_id_retrieval_rate": round(statistics.mean(row["citation_ids_in_retrieved"] for row in completed), 3) if completed else None,
        "refusal_or_review_accuracy": round(statistics.mean(row["status_correct"] for row in review), 3) if review else None,
        "batch_latency_ms": {"p50": round(statistics.median(timings), 3) if timings else None, "p95": round(max(timings), 3) if timings else None},
        "rows": rows,
    }


def main() -> None:
    blocks, queries = fixture()
    models = [item.strip() for item in os.environ.get("CODEX_QA_MODELS", "gpt-5.5,gpt-5.6-sol,gpt-5.6-luna").split(",") if item.strip()]
    query_ids = {item.strip() for item in os.environ.get("CODEX_QA_QUERY_IDS", "").split(",") if item.strip()}
    if query_ids:
        queries = [query for query in queries if query["id"] in query_ids]
    group_size = int(os.environ.get("CODEX_QA_GROUP_SIZE", "3"))
    timeout = float(os.environ.get("CODEX_QA_TIMEOUT_SECONDS", "60"))
    group_interval = float(os.environ.get("CODEX_QA_GROUP_INTERVAL_SECONDS", "5"))
    model_interval = float(os.environ.get("CODEX_QA_MODEL_INTERVAL_SECONDS", "10"))
    results = []
    for model_index, model in enumerate(models):
        if model_index:
            time.sleep(model_interval)
        parts = []
        for group_index in range(0, len(queries), group_size):
            if group_index:
                time.sleep(group_interval)
            parts.append(evaluate(model, queries[group_index:group_index + group_size], blocks, timeout))
        results.append(aggregate(model, parts))
    experiment_id = os.environ.get("CODEX_QA_EXPERIMENT_ID", "TECH-QA-030-R01")
    result = {
        "experiment_id": experiment_id,
        "scope": "complete fixed synthetic QA set through official Codex CLI in small batches",
        "data_sent": "project-authored synthetic fixture only; no user documents",
        "configuration": {
            "wire_api": "responses through official Codex provider",
            "reasoning_effort": os.environ.get("CODEX_QA_REASONING_EFFORT", "low"),
            "group_size": group_size,
            "timeout_seconds": timeout,
            "group_interval_seconds": group_interval,
            "model_interval_seconds": model_interval,
        },
        "providers": results,
        "boundary": "Grouped CLI latency includes official client startup and relay overhead; no direct Bearer API cost inference.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{experiment_id}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    scope_text = "完整固定 11 题" if not query_ids else "筛选题目 " + ",".join(query["id"] for query in queries)
    lines = [f"# {experiment_id} 官方 Codex CLI 分组文档问答评测", "", f"{scope_text}；仅发送项目自制合成证据。", "", "| 模型 | 完成 | JSON 合法率 | 状态准确率 | 引用来自检索证据 | 拒答/复核准确率 | 批次 p50/p95(ms) |", "|---|---:|---:|---:|---:|---:|---:|"]
    for item in results:
        def show(value): return "NA" if value is None else f"{value:.3f}" if isinstance(value, float) else str(value)
        lines.append(f"| {item['model']} | {item['completed_query_count']}/{item['query_count']} | {show(item['json_valid_rate'])} | {show(item['status_accuracy'])} | {show(item['citation_id_retrieval_rate'])} | {show(item['refusal_or_review_accuracy'])} | {item['batch_latency_ms']['p50']}/{item['batch_latency_ms']['p95']} |")
    lines.extend(["", "说明：这是固定问题集的分组结果；批次延迟不是单题 API p95，模型质量仍需人工 claim-level 复核。"])
    (OUT / f"{experiment_id}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"experiment_id": experiment_id, "providers": [{"model": item["model"], "completed": item["completed_query_count"], "status_accuracy": item["status_accuracy"]} for item in results]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
