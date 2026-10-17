# TECH-RET-009-R01 检索失败降级实验

降级优先保证可解释性和原文可核验性，不用无依据生成内容填补检索失败。

| 案例 | 失败状态 | 观察 | 降级动作 | 结果 |
|---|---|---|---|---|
| `D01` | no_answer_nonzero_overlap | 检索器返回了包含‘直接’的无关块，不能把词面命中当成答案存在。 | 停止生成事实回答；显示未找到支持性原文，并提供原文浏览/改写问题。 | PASS |
| `D02` | vector_index_unavailable | BM25 索引仍可独立返回关键词证据。 | 退回 BM25；在结果元数据标记 vector_unavailable，不改变权限过滤。 | PASS |
| `D03` | low_confidence_ocr_or_table_structure | 检索文本可能包含 OCR 错字或丢失行列关系。 | 返回页面图像/表格截图、低置信度警告和可核验位置；不生成精确数值结论。 | PASS |
| `D04` | evidence_location_missing | 无法对回答做引用校验。 | 降级为检索结果列表或原文阅读；禁止进入有引用要求的问答上下文。 | PASS |
