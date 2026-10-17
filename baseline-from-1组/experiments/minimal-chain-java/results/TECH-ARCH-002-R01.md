# TECH-ARCH-002-R01

## 实验目的

在不调用真实云端服务的前提下，使用同一解析器、检索器和模拟模型，验证本地优先、云端优先和混合路由的策略行为、证据链和降级路径。

## 结果

| 用例 | 模式 | 敏感级别 | 在线 | 云端允许 | 本地模型 | 实际路径 | 证据数 | 引用 | 拒答 | 路由符合预期 | 原因 |
|---|---|---|---|---|---|---|---:|---|---|---|---|
| ARCH-L-001 | LOCAL_FIRST | ORDINARY | true | true | true | LOCAL | 3 | PASS | false | true | 本地优先策略 |
| ARCH-C-001 | CLOUD_FIRST | ORDINARY | true | true | true | CLOUD_SIMULATED | 3 | PASS | false | true | CLOUD_FIRST允许普通文档使用模拟云端路径 |
| ARCH-H-001 | HYBRID | SENSITIVE | true | false | true | LOCAL | 3 | PASS | false | true | 未授权云端处理，留在本地路径 |
| ARCH-H-002 | HYBRID | ORDINARY | true | true | true | CLOUD_SIMULATED | 3 | PASS | false | true | HYBRID允许普通文档使用模拟云端路径 |
| ARCH-H-003 | HYBRID | ORDINARY | false | true | true | LOCAL | 3 | PASS | false | true | 网络不可用，切换本地路径 |
| ARCH-H-004 | HYBRID | SENSITIVE | false | false | false | LOCAL | 3 | PASS | true | true | 网络不可用，切换本地路径 |

## 原始事实

- 所有用例使用同一份 Markdown 样本、同一关键词检索器和同一模拟模型。
- `CLOUD_SIMULATED` 只表示路由选择，不代表真实云端服务的质量、成本或隐私政策。
- 敏感文档、未确认文档、离线场景均未路由到模拟云端路径。
- 本地模型不可用时，系统仍可返回拒答和证据链路状态。

## 项目组解释

当前接口能够把部署策略、文档策略和运行状态从解析/检索链路中分离；混合路由的策略行为可被记录和测试。

## 技术/需求建议

混合路由具备进入下一轮局部实验的接口基础，但当前实验不能证明云端质量、成本或真实数据合规性。下一步应将 PDF 解析适配器接入同一链路，执行 `TECH-DOC-xxx`，再回填本实验。

## 尚未验证

- PDF 双栏、扫描件、表格和公式的解析质量；
- 真实本地模型与云端模型的回答质量、时延和成本；
- 真实网络故障、云端限流和服务条款；
- 多文档权限过滤和索引版本变化。
