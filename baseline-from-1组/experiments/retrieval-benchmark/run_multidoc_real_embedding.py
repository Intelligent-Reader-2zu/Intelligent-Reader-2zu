"""Real local embedding multi-document retrieval comparison.

Uses the already cached BAAI/bge-small-zh-v1.5 model only on synthetic fixture
text.  Permission filtering is applied before ranking/fusion.  No external
network or real sensitive document is used.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
MODEL = ROOT / "models" / "bge-small-zh-v1.5"
sys.path.insert(0, str(ROOT))
from run_experiment import Index  # noqa: E402
from run_multidoc_experiment import fixture  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ranked_allowed(scores: list[float], blocks: list[dict], allowed: set[str], top_k: int) -> list[int]:
    candidates = [i for i, block in enumerate(blocks) if block["document_id"] in allowed and scores[i] > 0]
    return sorted(candidates, key=lambda i: (-scores[i], blocks[i]["document_id"], blocks[i]["block_id"]))[:top_k]


def fused_allowed(bm: list[float], vec: list[float], blocks: list[dict], allowed: set[str], top_k: int, k: int = 60) -> list[int]:
    candidates = [i for i, block in enumerate(blocks) if block["document_id"] in allowed and (bm[i] > 0 or vec[i] > 0)]
    bm_rank = sorted(candidates, key=lambda i: (-bm[i], blocks[i]["block_id"]))
    vec_rank = sorted(candidates, key=lambda i: (-vec[i], blocks[i]["block_id"]))
    fused = {i: 0.0 for i in candidates}
    for ranking in (bm_rank, vec_rank):
        for pos, idx in enumerate(ranking):
            fused[idx] += 1 / (k + pos + 1)
    return sorted(candidates, key=lambda i: (-fused[i], blocks[i]["block_id"]))[:top_k]


def main() -> None:
    blocks, queries = fixture()
    texts = [row["text"] for row in blocks]
    model = SentenceTransformer(str(MODEL), local_files_only=True, device="cpu")
    started = time.perf_counter()
    doc_vec = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    document_encoding_ms = (time.perf_counter() - started) * 1000
    index = Index(blocks)
    rows = []
    query_times = []
    methods = ("bm25", "vector_real", "hybrid_rrf_real")
    for query in queries:
        started = time.perf_counter()
        q_vec = model.encode([query["question"]], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)[0]
        vec_scores = np.asarray(doc_vec @ q_vec, dtype=float).tolist()
        bm_scores = index.bm25(query["question"])
        ids_by_method = {
            "bm25": ranked_allowed(bm_scores, blocks, query["allowed"], 8),
            "vector_real": ranked_allowed(vec_scores, blocks, query["allowed"], 8),
            "hybrid_rrf_real": fused_allowed(bm_scores, vec_scores, blocks, query["allowed"], 8),
        }
        elapsed = (time.perf_counter() - started) * 1000
        query_times.append(elapsed)
        methods_out = {}
        for method, ids in ids_by_method.items():
            returned = [blocks[i]["block_id"] for i in ids]
            gold = set(query["gold"])
            methods_out[method] = {
                "returned": returned,
                "gold_coverage": round(len(set(returned) & gold) / max(1, len(gold)), 3),
                "unauthorized_leak": any(blocks[i]["document_id"] not in query["allowed"] for i in ids),
                "source_versions": sorted({f"{blocks[i]['document_id']}@{blocks[i]['document_version']}" for i in ids}),
                "context_chars": sum(len(blocks[i]["text"]) for i in ids),
            }
        rows.append({"id": query["id"], "type": query["type"], "gold": sorted(query["gold"]), "methods": methods_out})

    summary = {}
    for method in methods:
        answerable = [row["methods"][method] for row in rows if row["gold"]]
        summary[method] = {
            "answerable_mean_coverage": round(statistics.mean(row["gold_coverage"] for row in answerable), 3),
            "unauthorized_leak_rate": round(sum(row["unauthorized_leak"] for row in (item["methods"][method] for item in rows)) / len(rows), 3),
            "mean_context_chars": round(statistics.mean(row["methods"][method]["context_chars"] for row in rows), 1),
            "query_p50_ms": round(statistics.median(query_times), 3),
            "query_p95_ms": round(sorted(query_times)[min(len(query_times) - 1, math.ceil(len(query_times) * 0.95) - 1)], 3),
        }

    scale = []
    for count in (1, 5, 10, 20, 50, 100, 500, 1000):
        scale_blocks = [dict(blocks[i % len(blocks)], document_id=f"SCALE-{i:03d}", block_id=f"SCALE-{i:03d}-v1-1-1") for i in range(count)]
        scale_texts = [row["text"] for row in scale_blocks]
        started = time.perf_counter()
        scale_vec = model.encode(scale_texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        encode_ms = (time.perf_counter() - started) * 1000
        scale_index = Index(scale_blocks)
        started = time.perf_counter()
        _ = scale_index.bm25("检索 证据 来源")
        bm25_ms = (time.perf_counter() - started) * 1000
        scale.append({"documents": count, "blocks": count, "embedding_encode_ms": round(encode_ms, 3), "bm25_query_ms": round(bm25_ms, 3), "embedding_dimension": int(scale_vec.shape[1])})

    model_files = [path for path in MODEL.rglob("*") if path.is_file()]
    result = {
        "experiment_id": "TECH-MDOC-005-011-R01",
        "scope": "real local embedding multi-document retrieval; synthetic fixture only; no cloud call",
        "model": "BAAI/bge-small-zh-v1.5",
        "model_revision": "7999e1d3359715c523056ef9478215996d62a620",
        "model_bytes": sum(path.stat().st_size for path in model_files),
        "model_sha256": {str(path.relative_to(MODEL)): sha256(path) for path in model_files},
        "device": "cpu",
        "embedding_dimension": int(doc_vec.shape[1]),
        "document_count": len(blocks),
        "document_encoding_ms": round(document_encoding_ms, 3),
        "summary": summary,
        "rows": rows,
        "scale": scale,
        "boundary": "This measures local embedding/retrieval plumbing on a small synthetic set. It does not establish semantic QA quality, production throughput, cloud cost, or deletion compliance.",
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "TECH-MDOC-005-011-R01.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# TECH-MDOC-005-011-R01 本地真实 embedding 多文档检索",
        "",
        f"模型：`BAAI/bge-small-zh-v1.5`，CPU，维度 `{result['embedding_dimension']}`；fixture 块数：{len(blocks)}；文档编码耗时：**{document_encoding_ms:.3f} ms**。权限过滤在排序和融合前执行。",
        "",
        "| 方法 | 有答案平均证据覆盖 | 未授权泄露率 | 平均上下文字符 | 查询 p50(ms) | 查询 p95(ms) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    labels = {"bm25": "BM25", "vector_real": "真实向量", "hybrid_rrf_real": "BM25 + 真实向量 RRF"}
    for method in methods:
        item = summary[method]
        lines.append(f"| {labels[method]} | {item['answerable_mean_coverage']:.3f} | {item['unauthorized_leak_rate']:.3f} | {item['mean_context_chars']:.1f} | {item['query_p50_ms']:.3f} | {item['query_p95_ms']:.3f} |")
    lines.extend([
        "",
        "## 规模记账",
        "",
        "| 文档/块数 | embedding 编码(ms) | BM25 查询(ms) | 维度 |",
        "|---:|---:|---:|---:|",
    ])
    lines.extend(f"| {item['documents']} | {item['embedding_encode_ms']:.3f} | {item['bm25_query_ms']:.3f} | {item['embedding_dimension']} |" for item in scale)
    lines.extend([
        "",
        "## 边界",
        "",
        "- 只使用项目自制合成文本和本地缓存模型，没有上传文档或调用云端服务。",
        "- 小样本结果不能证明跨文档生成回答、长上下文质量或真实业务语料召回。",
        "- 编码耗时是当前 CPU/运行时的观察值，不是并发吞吐或生产 SLA。",
        "- `TECH-MDOC-011` 的云端价格、服务时延、数据保留和删除验证仍未完成。",
    ])
    (OUT / "TECH-MDOC-005-011-R01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"experiment_id": result["experiment_id"], "summary": summary, "scale": scale}, ensure_ascii=False))


if __name__ == "__main__":
    main()
