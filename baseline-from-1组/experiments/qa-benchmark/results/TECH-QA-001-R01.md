# TECH-QA-001-R01 证据门控文档问答最小实验

本实验不调用生成模型，只验证问答链路在允许模型回答前的证据、拒答、冲突、引用和提示注入契约。

问题数：11；证据覆盖率：**0.778**；状态准确率：**0.818**；拒答/人工复核准确率：**1.000**；引用字段完整率：**1.000**；提示注入隔离：**PASS**；上下文平均字符数：**159.8**；基线 p50/p95：**0.120/0.169 ms**；模型成本：**0（未调用模型）**。

| 问题 | 类型 | 预期 | 实际 | 证据覆盖 | 引用完整 | 上下文字符 |
|---|---|---|---|---:|---|---:|
| Q01 | exact_keyword | answered | answered | 1.000 | PASS | 172 |
| Q02 | synonym_natural_language | answered | answered | 1.000 | PASS | 150 |
| Q03 | long_cross_paragraph | answered | refused | 0.000 | PASS | 170 |
| Q04 | table | answered | refused | 0.000 | PASS | 176 |
| Q05 | chinese | answered | answered | 1.000 | PASS | 170 |
| Q06 | multi_document | answered | answered | 1.000 | PASS | 175 |
| Q07 | answer_evidence | answered | answered | 1.000 | PASS | 172 |
| Q08 | no_answer | refused | refused | 0.000 | PASS | 155 |
| Q09 | unsupported_claim | refused | refused | 0.000 | PASS | 161 |
| Q10 | prompt_injection | needs_human_review | needs_human_review | 1.000 | PASS | 153 |
| Q11 | cross_document_conflict | needs_human_review | needs_human_review | 1.000 | PASS | 104 |

## 解释边界

- `status_accuracy` 反映的是证据门控和规则处理，不是语言模型正确率。
- `estimated_model_cost=0` 仅表示本实验没有外部调用；候选模型比较必须另行记录 token、计费、硬件和并发。
- 注入段落被视为不可信文档数据，不能获得系统/开发者指令权限；冲突答案进入人工复核。
