# Minimal Chain Java

这是智能阅读器 T07-A 的最小实验链路，不是产品原型。

当前链路：

```text
Markdown/TXT -> CanonicalDocument -> keyword retrieval
             -> Evidence -> MockModelAdapter -> citation check
```

## 运行环境

- Java 21+
- Maven 3.9+

## 运行

在本目录执行：

```powershell
mvn -q compile exec:java
```

也可以指定输入文件和查询：

```powershell
mvn -q compile exec:java '-Dexec.args=samples/reading-note.md "统一中间表示有什么作用"'
```

默认运行会读取 `samples/reading-note.md`，并将实验记录写入 `results/TECH-ARCH-001-R01.md`。

运行全局架构路由模拟实验：

```powershell
mvn -q compile
java -cp target/classes reader.experiment.GlobalExperimentMain
```

该实验生成 `results/TECH-ARCH-002-R01.md`。`CLOUD_SIMULATED` 只验证路由和接口行为，不会调用真实云端服务，也不能代表云端模型质量或服务条款。

运行 Evidence Contract 门控实验：

```powershell
mvn -q compile
java -cp target/classes reader.experiment.EvidenceGateExperimentMain
```

该实验生成 `results/TECH-ARCH-003-R01.md`。它不部署本地生成模型，也不调用真实云端服务，只验证云端准入、证据缺失阻断、人工复核、拒答和云端失败降级。

运行官方 Codex CLI 云端适配器架构实验：

```powershell
mvn -q compile
java -cp target/classes reader.experiment.CodexCloudArchitectureExperimentMain
```

该实验生成 `results/TECH-ARCH-004-R01.md`。它复用问答实验已验证的官方 `codex exec --ephemeral --sandbox read-only --skip-git-repo-check --ignore-rules --json` 路径，只向 CLI 发送项目自制合成 Evidence Contract。完整且允许外发的证据才会调用 CLI；缺少来源字段、禁止外部处理、低置信度、stale 文档和云端失败均保留本地证据/原文/人工复核降级。默认模型为 `gpt-5.6-sol`，可通过 `CODEX_ARCH_MODEL`、`CODEX_CLI_PATH` 和 `CODEX_ARCH_TIMEOUT_SECONDS` 覆盖。

## 当前实验边界

- 解析器只处理 Markdown/TXT 的行和段落，不代表 PDF 解析已经可行。
- 检索器是可解释的关键词基线，不代表向量检索或混合检索结论。
- 模型是模拟适配器，不调用本地或云端模型。
- 引用只验证回答引用的 block ID 是否来自检索证据。
- `TECH-ARCH-004-R01` 的成功只证明本次官方 CLI 路径对合成证据可调用并返回可解析 JSON，不代表真实文档质量、成本、SLA 或合规结论。

下一阶段可在不修改 `MinimalChain` 的情况下替换解析器、检索器和模型适配器。
