# 文档问答最小独立实验

`run_minimal_qa.py` 是一个不依赖外部 API、密钥或生成模型的问答链路实验。它读取 `retrieval-benchmark/dataset.json`，补充提示注入、跨文档冲突和完整证据元数据，验证：

- 证据覆盖和 top-k 检索失败是否会安全拒答；
- 跨文档冲突是否进入人工复核；
- 文档内提示注入是否保持为不可信数据；
- 结构化回答的状态、引用和来源字段是否完整；
- 上下文字符预算和规则链路 p50/p95 延迟。

运行：

```powershell
python experiments/qa-benchmark/run_minimal_qa.py
```

输出：

- `results/TECH-QA-001-R01.json`：逐题原始结构化结果；
- `results/TECH-QA-001-R01.md`：可读摘要。

边界：该实验的回答器是确定性的证据门基线，不是本地或云端语言模型。它不能给出生成质量、模型幻觉率、云端价格或本地吞吐的结论；真实模型比较必须使用同一问题集、同一证据包和同一人工评分协议另行记录。

多文档官方 CLI 对照：`run_multidoc_codex_cli.py` 沿用 `TECH-QA-030-R01` 的 Codex CLI/Responses、3 题分组和 60 秒超时配置，使用多文档专用的权限、版本、冲突和保密等级期望。仅发送项目自制合成证据；结果写入 `results/TECH-MDOC-011-R06/R07.*`。云端 token 成本、真实业务质量、数据保留和删除仍需单独验证。

本地环境门禁：

```powershell
python experiments/qa-benchmark/run_local_environment_gate.py
```

该检查只读取设备、运行时、模型文件和当前资源，不下载权重、不安装软件。结果写入 `results/TECH-QA-016-R01.*`，用于判断是否可以安全开始本地生成模型试验。

云端对比脚本：

```powershell
python experiments/qa-benchmark/run_cloud_qa.py
```

脚本只读取 `OPENAI_API_KEY`/`OPENAI_MODEL` 和 `DEEPSEEK_API_KEY`/`DEEPSEEK_MODEL`，只发送项目自制合成证据块；输出 `results/TECH-QA-017-R01.*`，不保存密钥。
