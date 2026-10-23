# TECH-CIT-001-R01 引用字段契约与锚点完整性

载入块数：**80**；核心字段完整率：**0.700**；物理页携带率：**0.550**；bbox 携带率：**0.550**；偏移长度一致率：**0.700**。

核心字段要求：`document_id`、`document_version`、`source_hash`、`block_id`、`section_path`、`paragraph`、`char_start`、`char_end`、`text`。

结论：该轮复用了已有解析 IR。字段完整率只证明定位数据是否存在，不证明回答 claim 被原文支持；bbox 和视觉高亮仍需渲染页金标准。
