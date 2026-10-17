# TECH-STRUCT-002-R01 统一结构 IR 映射

日期：2026-09-29  
范围：PDF、DOCX、Markdown、TXT 的统一结构中间表示（IR）适配；不修改生产 `DocumentBlock`，不评估问答正确率。

## 1. 实验目的

将不同解析器的结果映射为同一组元素字段，观察哪些信息可以跨格式统一、哪些信息必须保持格式特有，并用 `null` 显式表示缺失字段。适配器脚本为 `scripts/build_structure_ir.py`，原始结果位于 `results/text-structure/ir/`。

## 2. 统一字段

每份结果均记录：

```text
doc_id, source_hash, source_format
parser_name, parser_version, config_hash
element_id, element_type, text, normalized_text
ordinal, parent_element_id, children_ids, heading_path
heading_level, role, reading_order_index
physical_page, printed_page_label, bbox
char_start, char_end, source_line_start, source_line_end
confidence, asset_ref, style_ref
relations, warnings, field_completeness
```

`field_completeness` 是当前样本中非空元素的比例，不是准确率。例如 PDF 的 `bbox=1.0` 只说明每个输出文本元素有坐标，不说明它已经被正确合并成自然段。

## 3. 运行结果

| 样本 | 格式 | 元素数 | 标题数 | 表格数 | 物理页完整率 | bbox 完整率 | 源行完整率 |
|---|---|---:|---:|---:|---:|---:|---:|
| `SELF-001` | PDF | 10 | 0 | 0 | 1.00 | 1.00 | 0.00 |
| `SELF-002` | PDF | 24 | 0 | 0 | 1.00 | 1.00 | 0.00 |
| `SELF-003` | PDF | 10 | 0 | 0 | 1.00 | 1.00 | 0.00 |
| `SELF-005` | DOCX | 20 | 6 | 1 | 0.00 | 0.00 | 0.50 |
| `SELF-006` | DOCX | 22 | 5 | 1 | 0.00 | 0.00 | 0.41 |
| `SELF-007` | DOCX | 28 | 6 | 1 | 0.00 | 0.00 | 0.39 |
| `SELF-008` | Markdown | 17 | 4 | 0 | 0.00 | 0.00 | 1.00 |
| `SELF-009` | Markdown | 9 | 4 | 0 | 0.00 | 0.00 | 1.00 |
| `SELF-010` | TXT | 3 | 0 | 0 | 0.00 | 0.00 | 1.00 |
| `SELF-011` | TXT | 1 | 0 | 0 | 0.00 | 0.00 | 1.00 |

DOCX 标题数包含 `Title`；此前 `TECH-DOC-007-R01` 的 `heading_count` 只统计 `Heading 1..9`，两者口径不同，不能直接比较。

## 4. 观察和解释

### 4.1 PDF

- PyMuPDF 可以稳定提供物理页码、文本块 bbox、字符偏移和阅读顺序索引。
- 低层文本块不能直接当作语义标题、自然段、表格或脚注，因此 `heading` 和 `table` 数量为 0 是适配器边界，不是“文档没有标题/表格”。
- `SELF-002` 的双栏顺序问题仍然存在；IR 只是保留了原始顺序和坐标，没有替解析器修复阅读顺序。

### 4.2 DOCX

- `Title` 和 `Heading 1/2` 被映射为 `heading`，表格被映射为 `table -> table_cell` 子树，标题路径和父子 ID 可生成。
- 表格单元格没有段落行号，且 `python-docx` 逻辑读取不能提供最终视觉页码/bbox；这些字段保持 `null`。
- 当前适配器按 OOXML body 顺序读取段落和表格；列表、脚注、文本框、页眉页脚的语义关系仍需单独验证。

### 4.3 Markdown

- CommonMark 标题、段落、代码块和源行范围可以进入统一 IR；`SELF-009` 的 H2→H4→H3 跳级保持不变。
- 本轮未启用 GFM，因此表格、脚注和数学公式没有被宣称为结构元素；结果 warning 会随文档保存。
- Markdown 没有物理页和 bbox，后续引用应使用行号、字符偏移和稳定 `element_id`。

### 4.4 TXT

- UTF-8/GB18030 编码和空行段落可以统一为 paragraph 元素。
- TXT 没有原生标题层级、页码或布局；空行分组只是可复现的最低基线，不能解释为语义段落识别。

## 5. 适配器边界

本次明确保留以下差异，而不是强行填充：

| 字段 | PDF | DOCX | Markdown | TXT |
|---|---|---|---|---|
| `physical_page`/`bbox` | 可用 | 不可用 | 不适用 | 不适用 |
| `heading_level` | 本轮未推断 | 样式可用 | 语法可用 | 不适用 |
| `source_line_*` | 不适用 | OOXML body 序号部分可用 | 可用 | 可用 |
| `char_start/end` | 适配器拼接偏移 | 本轮未生成 | 部分可用 | 部分可用 |
| `table/cell` | 本轮未恢复网格 | 可用 | GFM 未启用 | 不适用 |
| `printed_page_label` | 本轮未识别 | 不稳定 | 不适用 | 不适用 |

## 6. 阶段结论

1. 统一 IR 可同时承载页级证据和逻辑结构，但不能消除格式差异；缺失字段必须显式保留。
2. 目录导航至少依赖 `heading_level + heading_path + parent_element_id`；PDF 当前低层结果还不能直接生成可靠目录。
3. PDF 引用优先使用 `physical_page + bbox + char offsets`；Markdown/TXT 使用行号/字符偏移；DOCX 需要渲染后页码或段落路径替代。
4. 结构化 JSON 比派生 Markdown 更适合作为事实来源；Markdown 只能作为可读视图或检索输入。
5. 当前结果证明接口形状和字段完整率可观测，不证明结构准确率；准确率需要人工金标准和下游定位实验。

## 7. 下一步

1. 在 IR 层加入 `relation`：脚注 marker、图注到图片、引用编号到参考文献、表格跨页分组。
2. 对 PDF 增加规则/模型标题候选、页眉页脚和表格网格，并与 `TECH-DOC-007-R02` 人工标注评分对接。
3. 对 Markdown 启用固定的 GFM/footnote/math 配置，补充表格、脚注、公式元素。
4. 对 DOCX 用固定渲染器生成页面图，把逻辑段落和视觉页码/bbox 关联起来。
5. 用固定检索问题验证 `element_id -> 标题路径 -> 原文位置` 的端到端引用回溯。
