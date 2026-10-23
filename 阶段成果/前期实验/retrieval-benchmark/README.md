# 文档检索最小对比实验

本实验使用项目组自制、离线、无外部服务的中文文档块，比较：

1. 关键词命中基线；
2. BM25；
3. TF-IDF 字符 n-gram 向量代理；
4. BM25 + 向量代理的 Reciprocal Rank Fusion (RRF) 混合检索。

另外，`run_real_ir_extension.py` 复用现有 OCR 文本和解析 IR，验证中文、数字、表格候选词与物理页回溯；`run_embedding_gate.py` 记录真实中文 embedding 的环境门禁。真实模型未取得前，`vector_proxy` 不得解释为 embedding 结论。

多文档离线最小实验：`run_multidoc_experiment.py` 使用项目自制合成文档，验证文档/版本/来源元数据、权限前置过滤、冲突保留、撤权/删除、保密等级默认拒绝、长文档来源配额和规模记账。它不调用生成模型或云端服务，不能替代真实 embedding、模型质量、并发、缓存/日志隔离或云端合规实验。结果写入 `results/TECH-MDOC-001-014-R01.{md,json}`。

本地真实 embedding 多文档对照：`run_multidoc_real_embedding.py` 使用已缓存的 `BAAI/bge-small-zh-v1.5`，在同一合成 fixture 上比较 BM25、真实向量和混合 RRF，并记录 1/5/10/20/50/100 个块的编码与查询耗时。它不调用云端，不代表生成回答质量或生产吞吐。结果写入 `results/TECH-MDOC-005-011-R01.{md,json}`。

本地持久化生命周期实验：`run_multidoc_lifecycle_experiment.py` 使用临时 SQLite FTS5 检查 ACL 撤权、缓存失效、版本 stale、删除传播、保密等级路由和 16 线程并发查询。它不证明生产向量库、备份或云端物理删除。结果写入 `results/TECH-MDOC-004-009-013-R01.{md,json}`。

真实模型文件放在 `models/bge-small-zh-v1.5/`，由 `run_real_embedding.py` 以 `local_files_only=True` 加载；模型文件哈希、revision、维度和归一化方式记录在 `results/TECH-RET-003-R02.json`。

TF-IDF 代理只用于验证实验链路、指标和证据定位，不代表真实 embedding 的语义能力。真实向量检索应在同一数据和问题集上替换为固定版本的中文 embedding，并记录模型、维度、归一化方式和索引版本。

运行：

```powershell
python experiments/retrieval-benchmark/run_experiment.py
```

输出：

- `results/TECH-RET-001-R01.json`：逐问题、逐方法的排名、指标、证据字段；
- `results/TECH-RET-001-R01.md`：可读结果摘要。
- `results/TECH-RET-003-R01.md`：真实中文 embedding 环境门禁记录。
- `results/TECH-RET-003-R02.md`：真实中文 embedding 对照结果。
- `results/TECH-RET-011-R01.md`：OCR/结构 IR 下游检索验证。
- `results/TECH-CIT-EXPERIMENTS-R01.md`：首轮引用链路汇总；包括字段契约、文本锚点、claim 支持性状态机、失败降级和 citation allow-list。
- `results/TECH-CIT-001-R01.md`、`TECH-CIT-003-R01.md`、`TECH-CIT-006-R01.md`、`TECH-CIT-010-R01.md`、`TECH-CIT-011-R01.md`：对应实验的可读结果；同名 `.json` 文件保留逐例数据。
- `results/TECH-CIT-FOLLOWUP-R01.md`：后续页码、bbox、章节稳定性、多文档冲突、OCR 降级、跳转路由和版本漂移实验汇总；对应 `TECH-CIT-002/004/005/007/008/009/012-R01`。

实验不测生成模型回答正确率，只测“回答所需证据是否被召回”和“证据定位是否保留”。

引用首轮实验运行：

```powershell
python experiments/retrieval-benchmark/run_citation_experiment.py
```

后续实验运行：

```powershell
python experiments/retrieval-benchmark/run_citation_followup.py
```

该首轮复用现有解析 IR，不声称已经验证 PDF 渲染高亮 IoU、真实用户跳转、DOCX 视觉分页稳定性或语义蕴含质量。
