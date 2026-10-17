# TECH-RET-007-R01 证据定位契约检查

检查证据数：95；完整证据数：0；完整率：0.000。

当前结果明确保留 `document_id`、`block_id`、页码、章节、段落和原文；版本、源哈希、字符偏移等缺失字段以 `null` 返回，不能把页码命中误写成完整引用链路。

## 必需字段

`document_id`, `document_version`, `source_hash`, `block_id`, `page`, `section_path`, `paragraph`, `char_start`, `char_end`, `text`

## 样例缺失

- `Q01` / `keyword` / `A-P1-B2`：缺少 document_version, source_hash, char_start, char_end
- `Q01` / `keyword` / `A-P1-B1`：缺少 document_version, source_hash, char_start, char_end
- `Q01` / `keyword` / `A-P2-B1`：缺少 document_version, source_hash, char_start, char_end
- `Q01` / `bm25` / `A-P1-B2`：缺少 document_version, source_hash, char_start, char_end
- `Q01` / `bm25` / `A-P1-B1`：缺少 document_version, source_hash, char_start, char_end
- `Q01` / `bm25` / `B-P2-B1`：缺少 document_version, source_hash, char_start, char_end
- `Q01` / `vector_proxy` / `A-P1-B2`：缺少 document_version, source_hash, char_start, char_end
- `Q01` / `vector_proxy` / `A-P1-B1`：缺少 document_version, source_hash, char_start, char_end
- `Q01` / `vector_proxy` / `B-P2-B1`：缺少 document_version, source_hash, char_start, char_end
- `Q01` / `hybrid_rrf` / `A-P1-B2`：缺少 document_version, source_hash, char_start, char_end
- `Q01` / `hybrid_rrf` / `A-P1-B1`：缺少 document_version, source_hash, char_start, char_end
- `Q01` / `hybrid_rrf` / `B-P2-B1`：缺少 document_version, source_hash, char_start, char_end
