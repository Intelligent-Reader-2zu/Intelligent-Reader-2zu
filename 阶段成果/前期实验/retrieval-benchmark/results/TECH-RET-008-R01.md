# TECH-RET-008-R01 多文档权限过滤实验

策略：先按允许的 `document_id` 过滤，再执行排序和融合；不可见文档不得进入 top-K，也不得通过检索结果泄露存在性。

| 方法 | 未授权泄露率 | 全部通过 | 有答案问题命中率 | 无答案仍返回结果 |
|---|---:|---|---:|---:|
| keyword | 0.000 | PASS | 1.000 | 1.000 |
| bm25 | 0.000 | PASS | 1.000 | 1.000 |
| vector_proxy | 0.000 | PASS | 1.000 | 1.000 |
| hybrid_rrf | 0.000 | PASS | 1.000 | 1.000 |

## 案例

- `P01` allowed=DOC-A gold=A-P3-B2
  - keyword: A-P3-B2,A-P1-B2,A-P2-B1; unauthorized_leak=False
  - bm25: A-P3-B2,A-P2-B2,A-P1-B2; unauthorized_leak=False
  - vector_proxy: A-P3-B2,A-P1-B2,A-P2-B1; unauthorized_leak=False
  - hybrid_rrf: A-P3-B2,A-P1-B2,A-P2-B1; unauthorized_leak=False
- `P02` allowed=DOC-A gold=(none)
  - keyword: A-P1-B2,A-P1-B1,A-P3-B1; unauthorized_leak=False
  - bm25: A-P1-B2,A-P3-B2,A-P1-B1; unauthorized_leak=False
  - vector_proxy: A-P3-B2,A-P1-B1,A-P1-B2; unauthorized_leak=False
  - hybrid_rrf: A-P3-B2,A-P1-B2,A-P1-B1; unauthorized_leak=False
- `P03` allowed=DOC-A,DOC-B gold=B-P2-B1
  - keyword: B-P2-B1,A-P2-B1,A-P2-B2; unauthorized_leak=False
  - bm25: B-P2-B1,A-P2-B1,A-P2-B2; unauthorized_leak=False
  - vector_proxy: B-P2-B1,A-P2-B1,A-P1-B1; unauthorized_leak=False
  - hybrid_rrf: B-P2-B1,A-P2-B1,A-P2-B2; unauthorized_leak=False
- `P04` allowed=DOC-A gold=(none)
  - keyword: A-P2-B1,A-P2-B2,A-P3-B2; unauthorized_leak=False
  - bm25: A-P2-B1,A-P2-B2,A-P3-B2; unauthorized_leak=False
  - vector_proxy: A-P2-B1,A-P1-B1,A-P1-B2; unauthorized_leak=False
  - hybrid_rrf: A-P2-B1,A-P1-B1,A-P2-B2; unauthorized_leak=False
