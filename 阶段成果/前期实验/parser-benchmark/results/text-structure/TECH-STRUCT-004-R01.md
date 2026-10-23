# TECH-STRUCT-004-R01 结构候选与格式扩展复测

日期：2026-09-29  
范围：Docling PDF 结构对照、Markdown GFM/脚注/公式扩展、DOCX OOXML 版面信号。

## 1. Docling PDF 对照

将已有 `Docling 2.130.0` 原始导出映射到统一 IR，并使用同一份 `SELF-001/002/003` 人工标注评分。OCR 和公式 enrichment 均关闭。

| 样本 | 预测元素 | 标题 | 段落 | 页脚 | 表格/单元格 | bbox 覆盖率 | 语义角色召回 | 脚注召回 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `SELF-001` | 18 | 3 | 3 | 2 | 1 / 9 | 0.8889 | 0.7778 | 0/1 |
| `SELF-002` | 27 | 6 | 8 | 3 | 1 / 9 | 0.6316 | 0.4737 | 0/1 |
| `SELF-003` | 18 | 3 | 3 | 2 | 1 / 9 | 0.8889 | 0.7778 | 0/1 |

表格网格三份样本均恢复为 3×3，单元格文本可用。`SELF-002` 双栏样本的覆盖率和语义角色召回明显较低，说明多栏阅读顺序和区域对应仍是主要风险。Docling 能识别页脚类型，但当前样本仍未把脚注标为独立语义类型。

原始结果：[`ir/docling-summary.json`](ir/docling-summary.json)、[`ir/docling-score.json`](ir/docling-score.json)。

## 2. Markdown 扩展

`markdown-it-py default` 对 `SELF-008` 的结构结果：

| 元素 | 数量 |
|---|---:|
| heading | 4 |
| paragraph | 10 |
| table | 1 |
| table_cell | 9 |
| code_block | 1 |
| equation | 1 |
| figure | 1 |
| footnote_definition | 1 |
| `table_contains_cell` | 9 |
| `footnote_marker_for` | 1 |

说明：表格由解析器 token 直接提供；脚注和数学公式使用保守源语法规则生成，关系目标必须能在源文档中定位。当前环境没有 `mdit-py-plugins`，所以没有把插件能力冒充为已验证能力；后续若固定插件版本，应另立实验编号。

原始结果：[`ir/SELF-008.markdown-extended.json`](ir/SELF-008.markdown-extended.json)。

## 3. DOCX 版面信号

本机没有 LibreOffice、Word 或其他固定渲染器，因此没有生成视觉页码或 bbox。改为检查 OOXML 中可观察的信号：

| 样本 | 显式分页符 | section 数 | 页眉部件 | 页脚部件 | 脚注部件 | 视觉页码 |
|---|---:|---:|---|---|---|---|
| `SELF-005` | 1 | 0 | `header1.xml` | `footer1.xml` | 有 | 不可用 |
| `SELF-006` | 1 | 0 | `header1.xml` | `footer1.xml` | 有 | 不可用 |
| `SELF-007` | 1 | 0 | `header1.xml` | `footer1.xml` | 有 | 不可用 |

这证明 DOCX 原始文件确实包含显式分页、页眉、页脚和脚注部件，但不能推导出最终页面布局。稳定页码仍需把渲染器作为受控实验依赖，或在产品上使用标题路径、段落索引和字符偏移替代。

原始结果：[`docx-layout.json`](docx-layout.json)。

## 4. 阶段结论

1. Docling 比 PyMuPDF 低层块更接近项目所需结构：能提供标题角色、页脚角色、表格网格、单元格 bbox 和父子关系；但双栏和脚注仍需验证，公式 enrichment 未测。
2. Markdown 在固定扩展规则后可以表达表格、代码、图片、公式和脚注关系；必须把方言/插件配置写入 `config_hash`。
3. DOCX 的逻辑结构和 OOXML 版面信号可以读取，但没有固定渲染器时不能承诺视觉页码；页码引用应先采用逻辑定位降级。
4. “字段可用”与“结构正确”仍需分开报告：Docling 表格网格形状正确不代表每个单元格文本正确；双栏 bbox 覆盖率低也不能由字符召回补偿。

## 5. 尚未完成的工作

- 真实授权网页材料的 DOM 标题、正文清理和动态页面实验；
- Docling 脚注、公式 enrichment 和跨页表格；
- GFM/脚注/数学插件固定版本后的回归；
- DOCX 固定渲染器下的视觉页码、页眉页脚 bbox 与脚注位置；
- 结构 IR 驱动的目录点击、段落检索和引用高亮端到端验证。

本轮没有修改生产解析模型，也没有把人工标注写入预测结果。
