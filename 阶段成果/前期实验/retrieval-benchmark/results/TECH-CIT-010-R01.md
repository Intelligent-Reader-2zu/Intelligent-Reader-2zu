# TECH-CIT-010-R01 引用失败降级与无依据拒答

| 用例 | 失败状态 | 期望动作 | 实际动作 | 结果 |
|---|---|---|---|---|
| `D01` | no_support | refuse | refuse | PASS |
| `D02` | location_missing | retrieval_or_original | retrieval_or_original | PASS |
| `D03` | low_confidence_ocr_or_table | page_image_warning | page_image_warning | PASS |
| `D04` | source_conflict | human_review | human_review | PASS |
| `D05` | exact_support | answer_with_citation | answer_with_citation | PASS |

结论：没有支持性原文时拒答；定位缺失时只给原文/检索入口；低置信度内容展示页面或截图并警告；冲突来源转人工复核。
