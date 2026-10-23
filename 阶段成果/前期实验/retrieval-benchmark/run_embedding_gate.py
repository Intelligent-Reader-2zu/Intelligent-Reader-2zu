import importlib.util
import json
import platform
import sys
from pathlib import Path


ROOT = Path(__file__).parent
OUT = ROOT / "results"


def main():
    packages = {name: bool(importlib.util.find_spec(name)) for name in ("sentence_transformers", "transformers", "torch", "faiss", "hnswlib")}
    result = {
        "experiment_id": "TECH-RET-003-R01",
        "status": "BLOCKED_ENVIRONMENT",
        "objective": "真实中文 embedding 在 SELF-RET-001 上与 BM25/RRF 对照",
        "requested_model": "BAAI/bge-small-zh-v1.5",
        "packages": packages,
        "python": sys.version,
        "platform": platform.platform(),
        "model_downloaded": False,
        "reason": "依赖已安装，但 BAAI/bge-small-zh-v1.5 模型下载在低速/重置连接下未完成，未取得完整模型文件；不得把 vector_proxy 当作真实 embedding 结论。",
        "rerun": "提供本地模型目录或可用的模型下载网络后，记录 commit、文件哈希、维度、归一化、编码和 ANN p50/p95，再运行同一问题集。",
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "TECH-RET-003-R01.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# TECH-RET-003-R01 真实中文 embedding 门禁", "",
        "状态：**BLOCKED_ENVIRONMENT**。本轮已尝试安装 `sentence-transformers==3.4.1`，下载过程中多次出现网络连接重置；当前未取得真实中文模型文件，因此没有执行伪装成真实向量的结果。", "",
        f"目标模型：`{result['requested_model']}`。当前包可用性：" + ", ".join(f"`{k}={'yes' if v else 'no'}`" for k, v in packages.items()) + ".", "",
        "已完成的 `vector_proxy` 只验证指标和证据链路，不用于模型选型。恢复条件是模型可下载或提供本地模型目录；随后固定模型提交/哈希、向量维度、归一化、索引参数，并与 BM25/RRF 比较 Recall@K、MRR、无答案误召回率、p50/p95 和资源占用。", "",
        "该阻塞已被显式记录，不影响一期保留 BM25、把向量作为可插拔增强的决策。",
    ]
    (OUT / "TECH-RET-003-R01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
