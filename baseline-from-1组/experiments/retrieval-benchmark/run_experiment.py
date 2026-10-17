import json
import math
import re
import time
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).parent
DATA = ROOT / "dataset.json"
OUT = ROOT / "results"


def tokens(text):
    # Chinese characters are individual searchable units; Latin and numbers stay as tokens.
    return re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9][a-zA-Z0-9._/-]*", text.lower())


def char_ngrams(text, n=2):
    compact = re.sub(r"\s+", "", text.lower())
    chars = list(compact)
    return ["".join(chars[i : i + n]) for i in range(max(0, len(chars) - n + 1))]


def cosine(a, b):
    da = sum(v * v for v in a.values())
    db = sum(v * v for v in b.values())
    if not da or not db:
        return 0.0
    return sum(a[k] * b.get(k, 0.0) for k in a) / math.sqrt(da * db)


class Index:
    def __init__(self, blocks):
        self.blocks = blocks
        self.tokenized = [tokens(b["text"] + " " + b.get("table_text", "")) for b in blocks]
        self.lengths = [len(t) for t in self.tokenized]
        self.avgdl = sum(self.lengths) / max(1, len(self.lengths))
        self.df = Counter(t for ts in self.tokenized for t in set(ts))
        self.N = len(blocks)
        self.char_docs = [Counter(char_ngrams(b["text"] + " " + b.get("table_text", ""))) for b in blocks]
        self.char_df = Counter(k for d in self.char_docs for k in d)

    def bm25(self, query):
        q = tokens(query)
        qf = Counter(q)
        k1, b = 1.2, 0.75
        scores = []
        for i, ts in enumerate(self.tokenized):
            tf = Counter(ts)
            score = 0.0
            for term, qcount in qf.items():
                if not tf[term]:
                    continue
                idf = math.log(1 + (self.N - self.df[term] + 0.5) / (self.df[term] + 0.5))
                denom = tf[term] + k1 * (1 - b + b * self.lengths[i] / max(self.avgdl, 1))
                score += idf * (tf[term] * (k1 + 1) / denom) * min(qcount, 2)
            scores.append(score)
        return scores

    def vector_proxy(self, query):
        # Sparse char n-gram TF-IDF proxy. It is intentionally labelled proxy in the report.
        q = Counter(char_ngrams(query))
        qv = {k: v * math.log(1 + self.N / (1 + self.char_df[k])) for k, v in q.items()}
        scores = []
        for d in self.char_docs:
            dv = {k: v * math.log(1 + self.N / (1 + self.char_df[k])) for k, v in d.items()}
            scores.append(cosine(qv, dv))
        return scores

    def keyword(self, query):
        q = set(tokens(query))
        return [sum(t in set(ts) for t in q) / max(1, len(q)) for ts in self.tokenized]


def rank(scores, topk):
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:topk]


def rank_positive(scores, topk):
    return [i for i in rank(scores, topk) if scores[i] > 0]


def rrf(bm, vec, topk, k=60):
    score = defaultdict(float)
    for ranking in (rank(bm, len(bm)), rank(vec, len(vec))):
        for pos, idx in enumerate(ranking):
            score[idx] += 1 / (k + pos + 1)
    return sorted(score, key=lambda i: (-score[i], i))[:topk], score


def evidence(block):
    return {
        "document_id": block["document_id"],
        "document_version": block.get("document_version"),
        "source_hash": block.get("source_hash"),
        "block_id": block["block_id"],
        "page": block["page"],
        "printed_page_label": block.get("printed_page_label"),
        "section_path": block["section_path"],
        "paragraph": block["paragraph"],
        "char_start": block.get("char_start"),
        "char_end": block.get("char_end"),
        "bbox": block.get("bbox"),
        "block_type": block["block_type"],
        "table_id": block.get("table_id"),
        "row_id": block.get("row_id"),
        "cell_id": block.get("cell_id"),
        "text": block["text"],
        "table_text": block.get("table_text"),
        "warnings": block.get("warnings", []),
    }


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    blocks = data["blocks"]
    queries = data["queries"]
    index = Index(blocks)
    methods = ("keyword", "bm25", "vector_proxy", "hybrid_rrf")
    results = {"experiment_id": "TECH-RET-001-R01", "dataset": data["dataset"], "index_stats": {"blocks": len(blocks), "token_postings": sum(len(set(ts)) for ts in index.tokenized), "char_ngram_postings": sum(len(d) for d in index.char_docs)}, "methods": {}, "queries": []}
    for method in methods:
        results["methods"][method] = {"top_k": 3, "scores_are_comparable": False if method != "hybrid_rrf" else False}
    for query in queries:
        timings = {}
        output = {"id": query["id"], "question": query["question"], "type": query["type"], "gold": query["gold"], "methods": {}}
        for method in methods:
            start = time.perf_counter()
            if method == "keyword":
                scores = index.keyword(query["question"])
                ids = rank_positive(scores, 3)
            elif method == "bm25":
                scores = index.bm25(query["question"])
                ids = rank_positive(scores, 3)
            elif method == "vector_proxy":
                scores = index.vector_proxy(query["question"])
                ids = rank_positive(scores, 3)
            else:
                bm, vec = index.bm25(query["question"]), index.vector_proxy(query["question"])
                ids, fusion_scores = rrf(bm, vec, 3)
                ids = [i for i in ids if bm[i] > 0 or vec[i] > 0]
            elapsed = (time.perf_counter() - start) * 1000
            hits = [blocks[i]["block_id"] for i in ids]
            relevant = set(query["gold"])
            hit_positions = [p + 1 for p, bid in enumerate(hits) if bid in relevant]
            output["methods"][method] = {
                "ranked_block_ids": hits,
                "recall_at_3": 1.0 if relevant.intersection(hits) else 0.0,
                "hit_rate": 1.0 if relevant.intersection(hits) else 0.0,
                "mrr": 1.0 / hit_positions[0] if hit_positions else 0.0,
                "false_positive_at_3": sum(b not in relevant for b in hits) / max(1, len(hits)),
                "nonzero_candidate": bool(ids),
                "abstention_correct": not relevant and not ids,
                "latency_ms": round(elapsed, 3),
                "evidence": [evidence(blocks[i]) for i in ids],
            }
            timings[method] = elapsed
        output["best_method_by_mrr"] = max(methods, key=lambda m: output["methods"][m]["mrr"])
        results["queries"].append(output)
    summary = {}
    for method in methods:
        rows = [q["methods"][method] for q in results["queries"]]
        answerable = [q["methods"][method] for q in results["queries"] if q["gold"]]
        no_answer = [q["methods"][method] for q in results["queries"] if not q["gold"]]
        latencies = sorted(r["latency_ms"] for r in rows)
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[min(len(latencies) - 1, math.ceil(len(latencies) * 0.95) - 1)]
        summary[method] = {
            "recall_at_3_answerable": round(sum(r["recall_at_3"] for r in answerable) / len(answerable), 3),
            "hit_rate_answerable": round(sum(r["hit_rate"] for r in answerable) / len(answerable), 3),
            "mrr_answerable": round(sum(r["mrr"] for r in answerable) / len(answerable), 3),
            "false_positive_at_3_answerable": round(sum(r["false_positive_at_3"] for r in answerable) / len(answerable), 3),
            "no_answer_false_positive_rate": round(sum(not r["abstention_correct"] for r in no_answer) / len(no_answer), 3),
            "mean_latency_ms": round(sum(r["latency_ms"] for r in rows) / len(rows), 3),
            "p50_latency_ms": round(p50, 3),
            "p95_latency_ms": round(p95, 3),
        }
    results["summary"] = summary
    OUT.mkdir(exist_ok=True)
    (OUT / "TECH-RET-001-R01.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# TECH-RET-001-R01 检索方式最小对比", "", "> 本结果只验证离线实验链路；`vector_proxy` 是字符 n-gram TF-IDF 代理，不是真实 embedding。指标中的 Recall@3、命中率和 MRR 只在 7 个有答案问题上计算；无答案问题单列误召回率。", "", f"索引规模：{results['index_stats']['blocks']} 个块，{results['index_stats']['token_postings']} 个词项倒排单元，{results['index_stats']['char_ngram_postings']} 个字符 n-gram 文档特征。", "", "## 汇总", "", "| 方法 | Recall@3 | 命中率 | MRR | Top-3 误召回率 | 无答案误召回率 | 平均延迟(ms) | p50 | p95 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    labels = {"keyword": "关键词", "bm25": "BM25", "vector_proxy": "向量代理", "hybrid_rrf": "混合 RRF"}
    for method in methods:
        s = summary[method]
        lines.append(f"| {labels[method]} | {s['recall_at_3_answerable']:.3f} | {s['hit_rate_answerable']:.3f} | {s['mrr_answerable']:.3f} | {s['false_positive_at_3_answerable']:.3f} | {s['no_answer_false_positive_rate']:.3f} | {s['mean_latency_ms']:.3f} | {s['p50_latency_ms']:.3f} | {s['p95_latency_ms']:.3f} |")
    lines += ["", "## 逐问题最佳方法", ""]
    for q in results["queries"]:
        lines.append(f"- `{q['id']}` {q['question']}：{labels[q['best_method_by_mrr']]}；gold={','.join(q['gold'])}")
    (OUT / "TECH-RET-001-R01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
