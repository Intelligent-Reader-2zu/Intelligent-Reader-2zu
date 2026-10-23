import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).parent
DATA = ROOT / "dataset.json"
MODEL = ROOT / "models" / "bge-small-zh-v1.5"
OUT = ROOT / "results"
sys.path.insert(0, str(ROOT))
from run_experiment import Index, rank_positive, rrf  # noqa: E402


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    blocks, queries = data["blocks"], data["queries"]
    texts = [b["text"] + " " + b.get("table_text", "") for b in blocks]
    model = SentenceTransformer(str(MODEL), local_files_only=True, device="cpu")
    dim = model.get_sentence_embedding_dimension()
    start = time.perf_counter()
    doc_vec = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    doc_ms = (time.perf_counter() - start) * 1000
    index = Index(blocks)
    rows = []
    for q in queries:
        start = time.perf_counter()
        q_vec = model.encode([q["question"]], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)[0]
        vec_scores = np.asarray(doc_vec @ q_vec, dtype=float).tolist()
        vector_ids = sorted(range(len(blocks)), key=lambda i: (-vec_scores[i], i))[:3]
        bm_scores = index.bm25(q["question"])
        bm_ids = rank_positive(bm_scores, 3)
        fused_ids, _ = rrf(bm_scores, vec_scores, 3)
        fused_ids = [i for i in fused_ids if bm_scores[i] > 0 or vec_scores[i] > 0]
        latency = (time.perf_counter() - start) * 1000
        methods = {"vector_real": vector_ids, "hybrid_rrf_real": fused_ids}
        output = {"id": q["id"], "question": q["question"], "gold": q["gold"], "methods": {}}
        for name, ids in methods.items():
            ranked = [blocks[i]["block_id"] for i in ids]
            gold = set(q["gold"])
            positions = [n + 1 for n, bid in enumerate(ranked) if bid in gold]
            output["methods"][name] = {
                "ranked_block_ids": ranked,
                "recall_at_3": float(bool(gold.intersection(ranked))),
                "hit_rate": float(bool(gold.intersection(ranked))),
                "mrr": 1 / positions[0] if positions else 0.0,
                "false_positive_at_3": sum(b not in gold for b in ranked) / max(1, len(ranked)),
                "nonzero_candidate": bool(ids),
                "abstention_correct": not gold and not ids,
                "latency_ms": round(latency, 3),
            }
        rows.append(output)
    methods = ("vector_real", "hybrid_rrf_real")
    summary = {}
    for method in methods:
        answerable = [r["methods"][method] for r in rows if r["gold"]]
        no_answer = [r["methods"][method] for r in rows if not r["gold"]]
        lats = sorted(r["methods"][method]["latency_ms"] for r in rows)
        summary[method] = {
            "recall_at_3_answerable": round(sum(r["recall_at_3"] for r in answerable) / len(answerable), 3),
            "hit_rate_answerable": round(sum(r["hit_rate"] for r in answerable) / len(answerable), 3),
            "mrr_answerable": round(sum(r["mrr"] for r in answerable) / len(answerable), 3),
            "false_positive_at_3_answerable": round(sum(r["false_positive_at_3"] for r in answerable) / len(answerable), 3),
            "no_answer_false_positive_rate": round(sum(not r["abstention_correct"] for r in no_answer) / len(no_answer), 3),
            "mean_query_ms": round(sum(lats) / len(lats), 3),
            "p50_query_ms": round(lats[len(lats) // 2], 3),
            "p95_query_ms": round(lats[min(len(lats) - 1, math.ceil(len(lats) * 0.95) - 1)], 3),
        }
    model_files = [p for p in MODEL.rglob("*") if p.is_file()]
    result = {
        "experiment_id": "TECH-RET-003-R02",
        "status": "PASS",
        "model": "BAAI/bge-small-zh-v1.5",
        "model_revision": "7999e1d3359715c523056ef9478215996d62a620",
        "model_file_sha256": {str(p.relative_to(MODEL)): sha256(p) for p in model_files},
        "model_bytes": sum(p.stat().st_size for p in model_files),
        "embedding_dimension": dim,
        "normalization": "L2/unit norm via normalize_embeddings=True; cosine equals dot product",
        "device": "cpu",
        "blocks": len(blocks),
        "queries": len(queries),
        "document_encoding_ms": round(doc_ms, 3),
        "summary": summary,
        "rows": rows,
        "boundary": "Small fixed synthetic set; model quality is not a production-scale or domain-gated conclusion.",
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "TECH-RET-003-R02.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# TECH-RET-003-R02 真实中文 embedding 对照", "", f"模型：`BAAI/bge-small-zh-v1.5`，revision `{result['model_revision']}`，维度 `{dim}`，L2 归一化，CPU。模型文件大小：{result['model_bytes'] / 1024 / 1024:.1f} MiB。", "", "| 方法 | Recall@3 | 命中率 | MRR | Top-3 误召回率 | 无答案误召回率 | 平均查询(ms) | p50 | p95 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    labels = {"vector_real": "真实向量", "hybrid_rrf_real": "BM25 + 真实向量 RRF"}
    for method in methods:
        s = summary[method]
        lines.append(f"| {labels[method]} | {s['recall_at_3_answerable']:.3f} | {s['hit_rate_answerable']:.3f} | {s['mrr_answerable']:.3f} | {s['false_positive_at_3_answerable']:.3f} | {s['no_answer_false_positive_rate']:.3f} | {s['mean_query_ms']:.3f} | {s['p50_query_ms']:.3f} | {s['p95_query_ms']:.3f} |")
    lines += ["", "模型文件 SHA-256 已写入同名 JSON；本结果替代不了大规模领域评测，仅解除真实模型链路的环境阻塞。"]
    (OUT / "TECH-RET-003-R02.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"experiment_id": result["experiment_id"], "status": result["status"], "summary": summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
