# TECH-ARCH-004-R01 官方 Codex CLI 云端适配器架构实验

本实验在 Evidence Contract 门控之后调用与问答实验相同的官方 `codex exec` 路径。仅发送项目自制合成证据，不读取或上传真实项目文档。

## 配置

- provider：官方 Codex CLI/Responses provider；未使用直接 OpenAI/Bearer API。
- executable：`C:\Users\联想\AppData\Local\OpenAI\Codex\bin\2e5e00daee91c61d\codex.exe`
- model：`gpt-5.6-sol`，reasoning effort：`low`
- timeout：60 秒；sandbox：`read-only`；调用参数包含 `--ephemeral --skip-git-repo-check --ignore-rules --json`。

## 结果

| 用例 | 门控 | 调用 CLI | CLI | JSON | status | 事件数 | citation IDs | 耗时(ms) | 降级/备注 |
|---|---|---:|---|---:|---|---:|---|---:|---|
| ARCH-004-001-CLOUD_ALLOWED 完整、已授权、高置信度证据 | ALLOW_CLOUD | 是 | SUCCESS | 是 | answered | 6 | DOC-001-B1 | 7084 | 无（进入回答后仍需引用校验） |
| ARCH-004-002-MISSING_HASH 缺少 source_hash | LOCAL_EVIDENCE_ONLY | 否 | NOT_CALLED | 否 | - | 0 | - | 0 | 保留本地证据、原文阅读或人工复核 |
| ARCH-004-003-EXTERNAL_FORBIDDEN 不允许外部处理 | LOCAL_EVIDENCE_ONLY | 否 | NOT_CALLED | 否 | - | 0 | - | 0 | 保留本地证据、原文阅读或人工复核 |
| ARCH-004-004-LOW_CONFIDENCE OCR 低置信度/结构风险 | HUMAN_REVIEW | 否 | NOT_CALLED | 否 | - | 0 | - | 0 | 保留本地证据、原文阅读或人工复核 |
| ARCH-004-005-STALE stale 文档版本 | REFUSE | 否 | NOT_CALLED | 否 | - | 0 | - | 0 | 保留本地证据、原文阅读或人工复核 |
| ARCH-004-006-CLI_FAILURE 云端 CLI 不可用，回退本地证据 | ALLOW_CLOUD | 是 | FAILED | 否 | - | 0 | - | 0 | 云端失败，退回本地证据和原文阅读 |

## 失败信息

- `ARCH-004-006-CLI_FAILURE`：CLI_NOT_FOUND: D:\Develop\Project\Intelligent-Reader\experiments\minimal-chain-java\missing-codex-cli.exe

## 模型输出可追溯摘要

- `ARCH-004-001-CLOUD_ALLOWED` final_text：{"status":"answered","answer":"统一中间表示用于隔离解析和下游模块。","citations":["DOC-001-B1"],"needs_human_review":false}

## 原始事实

1. Evidence Gate 阻断了缺失 source_hash、禁止外部处理、低置信度/结构风险和 stale 文档；这些用例的 CLI 调用次数为 0。
2. 完整且允许外发的合成证据进入了官方 CLI 适配器；是否成功、耗时和输出 JSON 合法性以本次运行记录为准。
3. CLI 不可用时，适配器返回失败状态，路由保持本地证据和原文阅读，不生成本地伪造答案。

## 项目组解释

云端生成应是受 Evidence Contract 约束的可替换适配器，而不是绕过权限、版本和引用校验的主链路。官方 CLI 可调用性只说明本次客户端路径具备实验可达性，不代表模型质量、成本、SLA、数据保留或长期稳定性。

## 技术/需求结论

当前全局架构可继续按“本地证据层 + 受控云端问答 + 无模型降级”推进；一期必须把门控拒绝、CLI 失败/超时、非法 JSON 和引用校验作为正式状态，而不是异常日志。

## 实验边界

- 云端输入为单条合成 Evidence Contract，未验证真实文档内容质量。
- 本实验没有比较云端供应商、价格、合规条款或本地生成模型。
- 成功输出仍需独立检查 citation ID 是否属于本次证据；模型返回 `answered` 不自动等于项目接受回答。
