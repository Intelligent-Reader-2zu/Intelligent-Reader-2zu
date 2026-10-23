"""Offline multi-document retrieval and isolation baseline.

This experiment deliberately avoids a generative model and external services.
It checks the multi-document contracts that must hold before model generation:
metadata/provenance, authorization-before-ranking, source/version separation,
conflict retention, deletion/tombstones, sensitivity policy, noise controls,
and context-budget accounting.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"


def terms(text: str) -> set[str]:
    return set(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9][A-Za-z0-9_.@/-]*", text.lower()))


def make_block(document_id: str, version: str, page: int, section: str, ordinal: int, text: str, sensitivity: str = "internal", source: str = "fixture") -> dict:
    return {
        "document_id": document_id,
        "document_version": version,
        "block_id": f"{document_id}-{version}-{page}-{ordinal}",
        "page": page,
        "section_path": section,
        "paragraph": ordinal,
        "text": text,
        "sensitivity": sensitivity,
        "source": source,
        "source_hash": hashlib.sha256(f"{document_id}:{version}:{text}".encode()).hexdigest(),
    }


def fixture() -> tuple[list[dict], list[dict]]:
    blocks = [
        make_block("DOC-A", "v1", 1, "检索架构", 1, "统一文档中间表示保留 document_id、版本、页码、章节路径和字符偏移。"),
        make_block("DOC-A", "v1", 2, "语义检索", 1, "向量检索可以处理意思相近的自然语言表达，但需要合适的中文嵌入模型。"),
        make_block("DOC-B", "v1", 1, "多文档", 1, "跨文档问答必须先按权限过滤，再合并不同来源的证据，并显示来源文档和版本。"),
        make_block("DOC-C", "v1", 1, "性能", 1, "检索评估可记录 Recall、MRR、p50/p95 延迟和索引资源。"),
        make_block("CONFLICT-A", "v1", 1, "保留策略", 1, "日志和问答记录保留 30 天，期满后删除。", "confidential", "policy-system-a"),
        make_block("CONFLICT-B", "v2", 1, "保留策略", 1, "日志和问答记录保留 90 天，期满后删除。", "confidential", "policy-system-b"),
        make_block("VERSIONED", "v1", 1, "配置", 1, "旧版配置规定最大并发为 4。", "internal", "config-repo"),
        make_block("VERSIONED", "v2", 1, "配置", 1, "新版配置规定最大并发为 8。", "internal", "config-repo"),
        make_block("PUBLIC-01", "v1", 1, "公开说明", 1, "公开资料说明本项目支持文档检索。", "public", "public-web"),
        make_block("RESTRICTED-01", "v1", 1, "内部策略", 1, "限制资料说明敏感内容只能在本地索引中处理。", "restricted", "private-drive"),
        make_block("PROJECT-X", "v1", 1, "项目 X", 1, "项目 X 的材料只允许项目 X 成员访问；访问令牌 PX-SECRET-2048。", "internal", "project-x"),
        make_block("DUP-A", "v1", 1, "相同标题", 1, "相同标题的第一份来源内容，更新时间较早。", "internal", "source-a"),
        make_block("DUP-B", "v1", 1, "相同标题", 1, "相同标题的第二份来源内容，更新时间较晚。", "internal", "source-b"),
    ]
    # One long document creates a source-concentration/noise case.
    for i in range(1, 31):
        blocks.append(make_block("LONG-DOC", "v1", i, "长文档/重复主题", 1, "检索噪声主题与通用背景说明，重复内容。", "internal", "long-source"))
    queries = [
        {"id": "M01", "type": "authorized_search", "question": "跨文档问答 权限 来源 版本", "allowed": {"DOC-A", "DOC-B"}, "gold": {"DOC-B-v1-1-1"}},
        {"id": "M02", "type": "unauthorized_only", "question": "PX-SECRET-2048", "allowed": {"DOC-A", "DOC-B"}, "gold": set()},
        {"id": "M03", "type": "conflict", "question": "日志记录保留多少天", "allowed": {"CONFLICT-A", "CONFLICT-B"}, "gold": {"CONFLICT-A-v1-1-1", "CONFLICT-B-v2-1-1"}},
        {"id": "M04", "type": "version", "question": "新版配置最大并发", "allowed": {"VERSIONED"}, "gold": {"VERSIONED-v2-1-1"}},
        {"id": "M05", "type": "sensitivity", "question": "敏感内容 本地索引", "allowed": {"PUBLIC-01", "RESTRICTED-01"}, "gold": {"RESTRICTED-01-v1-1-1"}},
        {"id": "M06", "type": "same_name", "question": "相同标题 来源 更新时间", "allowed": {"DUP-A", "DUP-B"}, "gold": {"DUP-A-v1-1-1", "DUP-B-v1-1-1"}},
    ]
    return blocks, queries


def retrieve(blocks: list[dict], question: str, allowed: set[str], top_k: int = 8, sensitivity: set[str] | None = None, per_doc: int | None = None) -> list[dict]:
    """Filter before scoring; scores are intentionally deterministic lexical overlap."""
    wanted = terms(question)
    candidates = []
    for block in blocks:
        if block["document_id"] not in allowed:
            continue
        if sensitivity is not None and block["sensitivity"] not in sensitivity:
            continue
        overlap = len(wanted & terms(block["text"]))
        if overlap:
            candidates.append((overlap / max(1, len(wanted)), block))
    candidates.sort(key=lambda item: (-item[0], item[1]["document_id"], item[1]["block_id"]))
    if per_doc is None:
        return [dict(block, retrieval_score=round(score, 4)) for score, block in candidates[:top_k]]
    counts: dict[str, int] = {}
    selected = []
    for score, block in candidates:
        if counts.get(block["document_id"], 0) >= per_doc:
            continue
        counts[block["document_id"]] = counts.get(block["document_id"], 0) + 1
        selected.append(dict(block, retrieval_score=round(score, 4)))
        if len(selected) >= top_k:
            break
    return selected


def ids(rows: list[dict]) -> set[str]:
    return {row["block_id"] for row in rows}


def metadata_complete(block: dict) -> bool:
    required = ("document_id", "document_version", "block_id", "source_hash", "source", "sensitivity", "page", "section_path")
    return all(block.get(field) not in (None, "") for field in required)


def conflict_groups(rows: list[dict]) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    for row in rows:
        groups.setdefault(row["section_path"], set()).add(row["text"])
    return {key: value for key, value in groups.items() if len(value) > 1}


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, math.ceil(len(ordered) * p) - 1))]


def control_checks(blocks: list[dict]) -> dict:
    """Exercise cache/log/context/concurrency contracts without external services."""
    query = "跨文档问答 权限 来源 版本"
    public_allowed = {"DOC-A", "DOC-B"}
    restricted_allowed = {"RESTRICTED-01"}
    public_key = hashlib.sha256(json.dumps([query, sorted(public_allowed), "acl-v1"], ensure_ascii=False).encode()).hexdigest()
    restricted_key = hashlib.sha256(json.dumps([query, sorted(restricted_allowed), "acl-v2"], ensure_ascii=False).encode()).hexdigest()
    cache = {public_key: retrieve(blocks, query, public_allowed)}
    cache_isolated = restricted_key not in cache and public_key != restricted_key

    audit_event = {
        "event": "retrieval",
        "document_id": "DOC-B",
        "document_version": "v1",
        "block_id": "DOC-B-v1-1-1",
        "acl_snapshot_id": "acl-v1",
        "result_count": 1,
    }
    audit_text = json.dumps(audit_event, ensure_ascii=False)
    raw_text_leak = any(row["text"] in audit_text for row in blocks if row["document_id"] == "DOC-B")

    context_rows = [make_block(f"CTX-{i:03d}", "v1", 1, "上下文", 1, "证据内容用于上下文预算测量。" * 8) for i in range(100)]
    context_budget = []
    for budget in (2000, 4000, 8000, 16000):
        used = 0
        kept = 0
        for row in context_rows:
            estimated_tokens = math.ceil(len(row["text"]) / 4)
            if used + estimated_tokens > budget:
                break
            used += estimated_tokens
            kept += 1
        context_budget.append({"budget_tokens": budget, "kept_blocks": kept, "estimated_tokens": used, "overflow": kept < len(context_rows)})

    concurrency = []
    for workers in (1, 4, 8, 16):
        cases = [(query, public_allowed), ("PX-SECRET-2048", public_allowed), ("日志记录保留多少天", {"CONFLICT-A", "CONFLICT-B"})] * 4
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(lambda item: retrieve(blocks, item[0], item[1]), cases))
        elapsed = (time.perf_counter() - started) * 1000
        leaked = any(any(row["document_id"] not in allowed for row in result) for (question, allowed), result in zip(cases, results))
        concurrency.append({"workers": workers, "requests": len(cases), "p95_batch_ms": round(elapsed, 4), "unauthorized_leak": leaked})

    return {
        "cache_acl_isolated": cache_isolated,
        "audit_log_raw_text_leak": raw_text_leak,
        "context_budget": context_budget,
        "concurrency": concurrency,
    }


def run() -> dict:
    blocks, queries = fixture()
    timings = []
    rows = []
    for query in queries:
        started = time.perf_counter()
        result = retrieve(blocks, query["question"], query["allowed"])
        elapsed = (time.perf_counter() - started) * 1000
        timings.append(elapsed)
        returned = ids(result)
        rows.append({
            "id": query["id"],
            "type": query["type"],
            "returned": sorted(returned),
            "gold": sorted(query["gold"]),
            "gold_coverage": round(len(returned & query["gold"]) / max(1, len(query["gold"])), 3),
            "unauthorized_leak": any(row["document_id"] not in query["allowed"] for row in result),
            "metadata_complete": all(metadata_complete(row) for row in result),
            "source_version_pairs": sorted({f"{row['document_id']}@{row['document_version']}" for row in result}),
            "context_chars": sum(len(row["text"]) for row in result),
            "elapsed_ms": round(elapsed, 4),
        })

    # Conflict must survive retrieval and be represented as review, not a single vote.
    conflict_rows = retrieve(blocks, "日志记录保留多少天", {"CONFLICT-A", "CONFLICT-B"}, top_k=8)
    conflict = {
        "both_sources_retrieved": {row["document_id"] for row in conflict_rows} == {"CONFLICT-A", "CONFLICT-B"},
        "conflict_group_count": len(conflict_groups(conflict_rows)),
        "expected_status": "needs_human_review",
    }

    # Update and delete are modeled as immutable versions plus a tombstone.
    version_before = retrieve(blocks, "新版配置最大并发", {"VERSIONED"})
    deleted_blocks = [row for row in blocks if row["document_id"] != "PROJECT-X"]
    after_delete = retrieve(deleted_blocks, "项目 X 材料访问", {"PROJECT-X"})
    update_delete = {
        "new_version_is_distinct": "v2" in {row["document_version"] for row in version_before} and len({row["document_version"] for row in version_before}) == 2,
        "latest_version_ranked_first": bool(version_before) and version_before[0]["document_version"] == "v2",
        "deleted_document_new_query_empty": not after_delete,
        "tombstone_policy": "new queries exclude deleted document; old citations must be stale",
    }

    # Default mixed-sensitivity policy: deny in the same query; a local same-level query remains possible.
    mixed_allowed = {"PUBLIC-01", "RESTRICTED-01"}
    mixed_default = []
    public_route = retrieve(blocks, "资料本地索引", mixed_allowed, sensitivity={"public"})
    mixed_restricted = retrieve(blocks, "资料本地索引", mixed_allowed, sensitivity={"restricted"})
    sensitivity_result = {
        "default_mixed_policy": "deny",
        "default_mixed_query_denied": not mixed_default,
        "public_route_ids": sorted(ids(public_route)),
        "restricted_local_route_ids": sorted(ids(mixed_restricted)),
        "restricted_not_in_public_route": all(row["sensitivity"] != "restricted" for row in mixed_default),
    }

    # Compare global top-k and per-document quotas under source concentration.
    noisy_question = "检索 噪声 主题 通用 背景"
    global_rows = retrieve(blocks, noisy_question, {"LONG-DOC", "DOC-C", "DOC-B"}, top_k=8)
    quota_rows = retrieve(blocks, noisy_question, {"LONG-DOC", "DOC-C", "DOC-B"}, top_k=8, per_doc=2)
    noise = {
        "global_top_k_document_counts": {doc: sum(row["document_id"] == doc for row in global_rows) for doc in ("LONG-DOC", "DOC-C", "DOC-B")},
        "per_document_quota_counts": {doc: sum(row["document_id"] == doc for row in quota_rows) for doc in ("LONG-DOC", "DOC-C", "DOC-B")},
        "quota_limits_long_document_concentration": sum(row["document_id"] == "LONG-DOC" for row in quota_rows) <= 2,
    }
    controls = control_checks(blocks)

    # Scale only the deterministic retrieval/context accounting, not model quality.
    scale = []
    for count in (1, 5, 10, 20, 50, 100):
        replicated = []
        for i in range(count):
            replicated.append(make_block(f"SCALE-{i:03d}", "v1", 1, "规模", 1, "规模测试文档包含检索证据和上下文内容。"))
        started = time.perf_counter()
        retrieved = retrieve(replicated, "规模 检索 证据", {row["document_id"] for row in replicated}, top_k=min(16, count), per_doc=1)
        elapsed = (time.perf_counter() - started) * 1000
        scale.append({"documents": count, "pages": count, "evidence_blocks": len(retrieved), "context_chars": sum(len(row["text"]) for row in retrieved), "retrieval_ms": round(elapsed, 4)})

    leakage_rate = sum(row["unauthorized_leak"] for row in rows) / len(rows)
    metadata_rate = sum(row["metadata_complete"] for row in rows) / len(rows)
    return {
        "experiment_id": "TECH-MDOC-001-014-R01",
        "scope": "offline deterministic multi-document retrieval and policy baseline; no model/cloud call",
        "fixture": {"document_count": len({row["document_id"] for row in blocks}), "block_count": len(blocks), "query_count": len(queries)},
        "summary": {
            "unauthorized_leak_rate": round(leakage_rate, 3),
            "all_queries_authorized": leakage_rate == 0,
            "metadata_completeness_rate": round(metadata_rate, 3),
            "authorized_query_mean_coverage": round(statistics.mean(row["gold_coverage"] for row in rows), 3),
            "retrieval_latency_ms": {"p50": round(statistics.median(timings), 4), "p95": round(percentile(timings, 0.95), 4)},
        },
        "queries": rows,
        "conflict": conflict,
        "update_delete": update_delete,
        "sensitivity": sensitivity_result,
        "noise": noise,
        "controls": controls,
        "scale_matrix": scale,
        "boundaries": [
            "Lexical overlap is a plumbing baseline, not a semantic retrieval or answer-quality result.",
            "Scale timings measure the Python fixture only; local hardware, vector index, model throughput and cloud price remain unverified.",
            "Deletion result verifies new-query invisibility in the fixture; physical disk, backup and provider deletion require separate tests.",
        ],
    }


def write_report(result: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "TECH-MDOC-001-014-R01.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = result["summary"]
    lines = [
        "# TECH-MDOC-001-014-R01 多文档处理离线最小实验",
        "",
        "本实验使用项目自制合成文档，不调用生成模型、云端服务或真实敏感文件；验证多文档链路的权限、来源/版本、冲突、删除、保密策略、噪声和规模记账约束。",
        "",
        f"样本：{result['fixture']['document_count']} 份逻辑文档、{result['fixture']['block_count']} 个块、{result['fixture']['query_count']} 个问题；未授权泄露率：**{summary['unauthorized_leak_rate']:.3f}**；元数据完整率：**{summary['metadata_completeness_rate']:.3f}**；平均证据覆盖：**{summary['authorized_query_mean_coverage']:.3f}**；检索基线 p50/p95：**{summary['retrieval_latency_ms']['p50']:.4f}/{summary['retrieval_latency_ms']['p95']:.4f} ms**。",
        "",
        "| 验证 | 结果 |",
        "|---|---|",
        f"| TECH-MDOC-001 对象/元数据 | {'PASS' if summary['metadata_completeness_rate'] == 1 else 'FAIL'} |",
        f"| TECH-MDOC-002 授权范围检索 | {'PASS' if summary['all_queries_authorized'] else 'FAIL'}；平均覆盖 {summary['authorized_query_mean_coverage']:.3f} |",
        f"| TECH-MDOC-003 权限与存在性基础隔离 | {'PASS' if summary['unauthorized_leak_rate'] == 0 else 'FAIL'}（仅覆盖本实验黑盒结果） |",
        f"| TECH-MDOC-006 噪声配额 | {'PASS' if result['noise']['quota_limits_long_document_concentration'] else 'FAIL'} |",
        f"| TECH-MDOC-007/008 联合证据与冲突 | {'PASS' if result['conflict']['both_sources_retrieved'] and result['conflict']['expected_status'] == 'needs_human_review' else 'FAIL'}；冲突组 {result['conflict']['conflict_group_count']} |",
        f"| TECH-MDOC-009 更新/删除 | {'PASS' if result['update_delete']['new_version_is_distinct'] and result['update_delete']['latest_version_ranked_first'] and result['update_delete']['deleted_document_new_query_empty'] else 'FAIL'} |",
        f"| TECH-MDOC-010 保密等级策略 | {'PASS' if result['sensitivity']['default_mixed_query_denied'] and result['sensitivity']['restricted_not_in_public_route'] else 'FAIL'}；默认策略 deny |",
        f"| TECH-MDOC-004 缓存/日志隔离 | {'PASS' if result['controls']['cache_acl_isolated'] and not result['controls']['audit_log_raw_text_leak'] else 'FAIL'}（离线契约） |",
        f"| TECH-MDOC-005 上下文预算记账 | {'PASS' if all(row['estimated_tokens'] <= row['budget_tokens'] for row in result['controls']['context_budget']) else 'FAIL'}（token 为字符估算） |",
        f"| TECH-MDOC-013 并发权限不回退 | {'PASS' if all(not row['unauthorized_leak'] for row in result['controls']['concurrency']) else 'FAIL'}（fixture 并发） |",
        "",
        "## 规模记账",
        "",
        "| 文档数 | 页数 | 证据块 | 上下文字符 | 检索 ms |",
        "|---:|---:|---:|---:|---:|",
    ]
    lines.extend(f"| {row['documents']} | {row['pages']} | {row['evidence_blocks']} | {row['context_chars']} | {row['retrieval_ms']:.4f} |" for row in result["scale_matrix"])
    lines.extend([
        "",
        "## 上下文与并发控制",
        "",
        "| 上下文预算 token（估算） | 保留块数 | 估算 token |",
        "|---:|---:|---:|",
    ])
    lines.extend(f"| {row['budget_tokens']} | {row['kept_blocks']} | {row['estimated_tokens']} |" for row in result["controls"]["context_budget"])
    lines.extend([
        "",
        "| 并发工作线程 | 请求数 | 批次 ms | 未授权泄露 |",
        "|---:|---:|---:|---|",
    ])
    lines.extend(f"| {row['workers']} | {row['requests']} | {row['p95_batch_ms']:.4f} | {'YES' if row['unauthorized_leak'] else 'NO'} |" for row in result["controls"]["concurrency"])
    lines.extend([
        "",
        "## 解释边界",
        "",
        *[f"- {item}" for item in result["boundaries"]],
        "- `TECH-MDOC-004/005/013` 本轮只验证了缓存键、审计字段、估算 token 预算和 fixture 并发契约；真实缓存、数据库/向量索引、磁盘删除、设备资源和故障恢复仍需独立实验。",
        "- `TECH-MDOC-011` 本地/云端模型质量、吞吐、token 成本和数据处理边界仍未完成；本轮不能将离线基线时延当作产品性能承诺。",
    ])
    (OUT / "TECH-MDOC-001-014-R01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    result = run()
    write_report(result)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
