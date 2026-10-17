# TECH-STRUCT-003-R01 关系边和结构角色评分

日期：2026-09-29  
范围：统一 IR 的父子关系、脚注关系、表格单元格关系，以及三份已确认 PDF 标注上的语义角色/表格网格评分。

## 1. 实验内容

新增两个实验脚本：

- `scripts/enrich_structure_relations.py`：只根据可观察的父子 ID、Markdown 源文和元素文本生成关系边；无法找到目标时不生成虚假边。
- `scripts/score_structure_relations.py`：使用已有人工标注评估低层 PDF IR 的元素覆盖、语义角色和表格网格可用性。

关系类型：

```text
contains                 标题 -> 子元素、表格 -> 单元格
table_contains_cell      table -> table_cell
footnote_marker_for      Markdown 脚注标记 -> 脚注定义
citation_refers_to       [n] -> [n] 参考文献（本轮样本未形成有效目标）
```

## 2. 关系生成结果

| 样本 | 关系结果 |
|---|---|
| `SELF-001/002/003` PDF | 0 条语义关系；低层块没有标题、脚注或表格网格类型 |
| `SELF-005` DOCX | 16 条 `contains`，9 条 `table_contains_cell` |
| `SELF-006` DOCX | 18 条 `contains`，12 条 `table_contains_cell` |
| `SELF-007` DOCX | 23 条 `contains`，16 条 `table_contains_cell` |
| `SELF-008` Markdown | 16 条 `contains`，1 条 `footnote_marker_for` |
| `SELF-009` Markdown | 8 条 `contains` |
| `SELF-010/011` TXT | 没有可安全推断的关系 |

原始关系摘要：[`ir/relation-summary.json`](ir/relation-summary.json)。关系已回写到各样本 IR JSON 的 `relations` 字段。

## 3. 人工标注评分

| 样本 | Gold 单元 | 预测元素 | 元素匹配数 | bbox 覆盖率 | 语义角色召回 | 脚注语义召回 | 表格网格 |
|---|---:|---:|---:|---:|---:|---:|---|
| `SELF-001` | 9 | 10 | 6 | 0.6667 | 0.2222 | 0/1 | 不可用 |
| `SELF-002` | 19 | 24 | 9 | 0.4737 | 0.0526 | 0/1 | 不可用 |
| `SELF-003` | 9 | 10 | 6 | 0.6667 | 0.2222 | 0/1 | 不可用 |

评分原始结果：[`ir/relation-score.json`](ir/relation-score.json)。

这些分数只评价当前 PyMuPDF 低层适配器是否已经携带人工标注所要求的语义类型；它们不等价于 PyMuPDF 的字符召回率，也不代表 Docling、pdfplumber 或 OCR 路径的结果。

## 4. 解释

1. DOCX 的逻辑树可以直接产生标题到段落、表格到单元格的 `contains` 边，因此目录导航和表格局部检索有可用的数据基础。
2. Markdown 的源语法提供脚注标记和定义位置，能够生成 `footnote_marker_for`；该关系依赖固定方言，未知扩展仍需保留原文。
3. TXT 没有天然父子或引用语义，不能仅凭空行推断关系。
4. PDF 的 PyMuPDF `DICT` 结果保留了页面和 bbox，但本轮适配器没有把视觉模式推断成标题、脚注或表格，因此人工标注中的脚注、页脚和表格关系没有被恢复。
5. `SELF-002` 的 bbox 覆盖率低于单栏样本，说明双栏/表格区域的低层块与人工语义单元不是一一对应；不能用字符完整代替结构覆盖。

## 5. 对产品能力的影响

- **目录导航**：需要 heading 的 `contains` 边和稳定 `heading_path`；PDF 低层块未分类时只能提供页面级阅读。
- **段落检索**：关系边可以把检索块扩展到所属章节；没有关系时只能按相邻文本扩大上下文，风险更高。
- **表格问答**：必须有 table/cell 和行列字段；当前 PDF 适配器只能降级为线性文本或截图。
- **脚注/引用定位**：必须有 marker 到目标的关系；没有目标时应显示未解析，而不是把脚注正文拼入答案。
- **证据回溯**：关系边必须与 `element_id`、页码/行号和源哈希一起保存，解析器升级后才能解释答案变化。

## 6. 结论和下一步

本轮证明关系字段可以加入统一 IR，并能明确区分“已有关系”“关系未解析”和“格式本身没有关系语义”。下一步应：

1. 用 Docling/Unstructured 输出补齐 PDF 标题、页脚、脚注和表格候选，再用同一关系评分比较。
2. 为 Markdown 固定 GFM/footnote/math 配置，补测表格、脚注和公式关系。
3. 为 DOCX 增加列表项、脚注、页眉页脚和渲染页码关系。
4. 将关系完整率接入固定检索问题，验证“命中块 -> 所属章节 -> 原始位置”的引用链。

本轮未修改生产模型，也没有把人工标注写回为预测结果。
