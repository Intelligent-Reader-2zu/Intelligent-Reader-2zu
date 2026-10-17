# TECH-RET-003-R01 真实中文 embedding 门禁

状态：**BLOCKED_ENVIRONMENT**。`sentence-transformers==3.4.1`、`transformers==4.57.6` 和 `torch==2.14.0` 已安装，但 `BAAI/bge-small-zh-v1.5` 下载在低速/连接重置下未完成，当前未取得完整模型文件，因此没有执行伪装成真实向量的结果。

目标模型：`BAAI/bge-small-zh-v1.5`。当前包可用性：`sentence_transformers=yes`, `transformers=yes`, `torch=yes`, `faiss=no`, `hnswlib=no`.

已完成的 `vector_proxy` 只验证指标和证据链路，不用于模型选型。恢复条件是提供本地模型目录或可用的模型下载网络；随后固定模型提交/哈希、向量维度、归一化、索引参数，并与 BM25/RRF 比较 Recall@K、MRR、无答案误召回率、p50/p95 和资源占用。

该阻塞已被显式记录，不影响一期保留 BM25、把向量作为可插拔增强的决策。
