# TECH-ARCH-003-R01 Evidence Contract 门控实验

本实验不调用真实云端服务，也不部署本地生成模型；只验证证据契约、云端准入和失败降级。

| 用例 | 门控决定 | 模拟云端状态 | 降级动作 |
|---|---|---|---|
| ARCH-GATE-001 | ALLOW_CLOUD | SUCCESS | 无 |
| ARCH-GATE-002 | LOCAL_EVIDENCE_ONLY | NOT_CALLED | 保留本地证据、原文阅读或人工复核 |
| ARCH-GATE-003 | LOCAL_EVIDENCE_ONLY | NOT_CALLED | 保留本地证据、原文阅读或人工复核 |
| ARCH-GATE-004 | HUMAN_REVIEW | NOT_CALLED | 保留本地证据、原文阅读或人工复核 |
| ARCH-GATE-005 | REFUSE | NOT_CALLED | 保留本地证据、原文阅读或人工复核 |
| ARCH-GATE-006 | ALLOW_CLOUD | FORBIDDEN | 云端失败，退回本地证据和原文阅读 |

## 阶段性结论

- 完整、已授权且高置信度证据才进入模拟云端路径。
- 缺少版本、源哈希或定位字段时不调用云端，退回本地证据。
- 敏感、stale、低置信度或结构风险证据不自动生成回答。
- 云端拒绝/不可用时保留本地证据和原文阅读。
- 本实验不能证明真实云端模型质量、费用、时延或合规性。
