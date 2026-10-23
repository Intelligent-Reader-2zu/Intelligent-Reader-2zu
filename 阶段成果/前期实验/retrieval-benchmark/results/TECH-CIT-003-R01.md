# TECH-CIT-003-R01 文本锚点、字符偏移与漂移恢复

测试用例：**5**；通过率：**1.000**。

| 用例 | 场景 | 期望 | 实际 | 结果 |
|---|---|---|---|---|
| `L01` | exact | exact | exact | PASS |
| `L02` | normalized_quote | recovered | recovered | PASS |
| `L03` | stale_version | stale | stale | PASS |
| `L04` | invalid_offset | invalid | invalid | PASS |
| `L05` | page_only_fallback | page_only | page_only | PASS |

结论：精确 offset、规范化恢复、版本失效、越界和页级降级可以在服务端区分，不能把恢复定位伪装成 exact。
