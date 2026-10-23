# TECH-CIT-006-R01 Claim 原文支持性探针

用例数：**3**；规则性分类通过率：**1.000**。

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| `S01` | entailed | entailed | PASS |
| `S02` | partially_supported | partially_supported | PASS |
| `S03` | not_supported | not_supported | PASS |

边界：词面重叠不等于语义蕴含。本结果只验证状态机输入输出和拒答方向，不能宣称模型回答正确率。
