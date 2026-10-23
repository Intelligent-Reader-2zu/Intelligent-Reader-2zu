# TECH-QA-024-R01 Responses-only relay request

日期：2026-10-12

本次只向 `https://api.ipc.wiki/v1/responses` 发送一个合成最小请求：

- 模型：`gpt-5.5`
- 认证变量：`OPENAI_KEY`（仅在进程内映射为请求凭据，不写入文件）
- 请求体：`model`、`instructions`、`input`、`max_output_tokens`、`store=false`
- 未访问 `/models`
- 未调用 `/chat/completions`
- 未上传项目文档

结果：请求通过原始 HTTP 客户端到达中转站，并返回 `HTTP 403`。随后又按 `D:/Develop/Project/agent-collaborate/src/main/java/com/example/agentcollab/client/OpenAiAgentProviderClient.java` 的实际字段复现了一次：`input` 字符串、`stream:false`、`store:false`、`Accept: application/json`，仍返回 `HTTP 403`。中转站错误为账号/客户端策略拒绝，不能作为模型质量结果。未伪造 Codex 官方客户端身份，也未绕过该策略。

下一步需要使用中转站明确允许的客户端协议，或由用户提供其 Web 项目中实际成功请求所使用的非敏感请求头/客户端配置；仅改变 Responses 请求体字段无法解除账号策略拒绝。
