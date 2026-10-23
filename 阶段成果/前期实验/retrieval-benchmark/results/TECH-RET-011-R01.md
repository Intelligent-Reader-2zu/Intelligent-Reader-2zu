# TECH-RET-011-R01 OCR 与结构 IR 检索下游验证

OCR 固定查询页命中率 Hit@3：**1.000**；结构 IR Hit@3：**1.000**；OCR 证据页码携带率：**1.000**。

该实验复用现有 Tesseract OCR 文本和解析 IR，验证中文、英文、数字、表格候选词能否回到物理页。它不替代 CER/WER，也不代表真实向量检索质量；OCR 文本中的字符错误仍需原页核验。

| 用例 | 类型 | 查询 | 返回页 | 命中 | 原文 | 页码 |
|---|---|---|---|---|---|---|
| OCR-01 | ocr | OCR TEST | 1,2 | YES | YES | YES |
| OCR-02 | ocr | 12345 | 1,2 | YES | YES | YES |
| OCR-03 | ocr | 物理页码 | 1,2 | YES | YES | YES |
| OCR-04 | ocr | A-01 | 1,2 | YES | YES | YES |
| OCR-05 | ocr | 表格候选单元格 | 1,2 | YES | YES | YES |
| IR-01 | structured_ir | Recall@k | 1 | YES | YES | NO |
| IR-02 | structured_ir | physical_page | 1 | YES | YES | YES |
| IR-03 | structured_ir | heading_path | 1 | YES | YES | YES |
| IR-04 | structured_ir | 参考文献 | 1 | YES | YES | NO |
