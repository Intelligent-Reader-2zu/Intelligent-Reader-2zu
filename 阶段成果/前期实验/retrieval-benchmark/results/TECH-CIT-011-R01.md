# TECH-CIT-011-R01 模型引用白名单与伪造字段拦截

白名单 citation 数：**80**；测试通过率：**1.000**。

| 用例 | 模型返回值 | 期望允许 | 实际允许 | 结果 |
|---|---|---:|---:|---|
| `W01` | `self-001-0391dd982a1c::self-001-0391dd982a1c-e0001` | True | True | PASS |
| `W02` | `forged::citation` | False | False | PASS |
| `W03` | `self-001-0391dd982a1c::self-001-0391dd982a1c-e0001::forged-page` | False | False | PASS |

结论：服务端只接受检索证据中的 citation_id；页码、quote 和坐标由服务端证据记录解析，模型不能自由编造。
