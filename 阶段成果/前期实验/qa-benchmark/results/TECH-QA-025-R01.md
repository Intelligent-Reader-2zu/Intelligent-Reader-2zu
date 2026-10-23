# TECH-QA-025-R01 当前中转站参数审计

日期：2026-10-12

## 当前 Codex 配置

读取自 `C:/Users/联想/.codex/config.toml`：

- `model_provider=custom`
- `model=gpt-5.6-sol`
- `model_reasoning_effort=high`
- `base_url=https://api.ipc.wiki`
- `wire_api=responses`
- `requires_openai_auth=true`

注意：当前配置不是此前实验脚本使用的 `https://api.ipc.wiki/v1`、`requires_openai_auth=false`。Codex 客户端负责根据 provider 配置构造实际请求，并使用其官方认证链路。

## 实测

使用本机已安装的官方 Codex CLI、`--ephemeral`、只读沙箱、合成提示，分别指定三个候选模型：

| 模型 | 结果 |
|---|---|
| `gpt-5.5` | 成功，返回预期 JSON；CLI 调用约 13 秒 |
| `gpt-5.6-sol` | 成功，返回预期 JSON；CLI 调用约 15 秒 |
| `gpt-5.6-luna` | 成功，返回预期 JSON；CLI 调用约 15 秒 |

## 结论

通用 Java/Python 请求使用 `OPENAI_KEY` 到同一中转站会返回 `HTTP 403 This account only allows Codex official clients`；这不是 Responses 请求体字段问题，而是账号/客户端认证策略。不能通过伪造官方客户端标识解决。后续云端问答评测应使用官方 Codex CLI 适配器，或使用中转站明确允许第三方 API 的独立账号/密钥。

本记录只证明候选模型在官方客户端链路可调用，不代表文档问答质量、拒答质量、成本或长期稳定性。
