# TECH-MDOC-001-014-R01 多文档处理离线最小实验

本实验使用项目自制合成文档，不调用生成模型、云端服务或真实敏感文件；验证多文档链路的权限、来源/版本、冲突、删除、保密策略、噪声和规模记账约束。

样本：12 份逻辑文档、43 个块、6 个问题；未授权泄露率：**0.000**；元数据完整率：**1.000**；平均证据覆盖：**0.833**；检索基线 p50/p95：**0.0147/0.6529 ms**。

| 验证 | 结果 |
|---|---|
| TECH-MDOC-001 对象/元数据 | PASS |
| TECH-MDOC-002 授权范围检索 | PASS；平均覆盖 0.833 |
| TECH-MDOC-003 权限与存在性基础隔离 | PASS（仅覆盖本实验黑盒结果） |
| TECH-MDOC-006 噪声配额 | PASS |
| TECH-MDOC-007/008 联合证据与冲突 | PASS；冲突组 1 |
| TECH-MDOC-009 更新/删除 | PASS |
| TECH-MDOC-010 保密等级策略 | PASS；默认策略 deny |
| TECH-MDOC-004 缓存/日志隔离 | PASS（离线契约） |
| TECH-MDOC-005 上下文预算记账 | PASS（token 为字符估算） |
| TECH-MDOC-013 并发权限不回退 | PASS（fixture 并发） |

## 规模记账

| 文档数 | 页数 | 证据块 | 上下文字符 | 检索 ms |
|---:|---:|---:|---:|---:|
| 1 | 1 | 1 | 19 | 0.0142 |
| 5 | 5 | 5 | 95 | 0.0243 |
| 10 | 10 | 10 | 190 | 0.0393 |
| 20 | 20 | 16 | 304 | 0.0734 |
| 50 | 50 | 16 | 304 | 0.1642 |
| 100 | 100 | 16 | 304 | 0.3151 |

## 上下文与并发控制

| 上下文预算 token（估算） | 保留块数 | 估算 token |
|---:|---:|---:|
| 2000 | 71 | 1988 |
| 4000 | 100 | 2800 |
| 8000 | 100 | 2800 |
| 16000 | 100 | 2800 |

| 并发工作线程 | 请求数 | 批次 ms | 未授权泄露 |
|---:|---:|---:|---|
| 1 | 12 | 1.9639 | NO |
| 4 | 12 | 1.2402 | NO |
| 8 | 12 | 0.8883 | NO |
| 16 | 12 | 0.8588 | NO |

## 解释边界

- Lexical overlap is a plumbing baseline, not a semantic retrieval or answer-quality result.
- Scale timings measure the Python fixture only; local hardware, vector index, model throughput and cloud price remain unverified.
- Deletion result verifies new-query invisibility in the fixture; physical disk, backup and provider deletion require separate tests.
- `TECH-MDOC-004/005/013` 本轮只验证了缓存键、审计字段、估算 token 预算和 fixture 并发契约；真实缓存、数据库/向量索引、磁盘删除、设备资源和故障恢复仍需独立实验。
- `TECH-MDOC-011` 本地/云端模型质量、吞吐、token 成本和数据处理边界仍未完成；本轮不能将离线基线时延当作产品性能承诺。
