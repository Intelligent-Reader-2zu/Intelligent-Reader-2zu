# TECH-DOC-007-R02 人工结构标注模板

本模板用于补充自动检查无法可靠推断的金标准。当前轮次不做 OCR；只标注文本层 PDF `SELF-001` 至 `SELF-003`。不要根据某个解析器的输出直接复制标注，必须以渲染页面和原始样本为准。

## 标注人需要填写的内容

每个样本至少记录：

1. 每个可评价单元的人工阅读顺序 `reading_order_rank`；跨栏时按页面的自然阅读顺序编号。
2. 单元类型：`title`、`paragraph`、`table`、`table_cell`、`footnote`、`header`、`footer`、`reference`、`figure_caption` 或 `other`。
3. 标题层级：普通正文填 `null`，标题填写 `1`、`2` 等；不要为了连续而修正原文标题编号。
4. 段落归属：同一自然段使用相同 `paragraph_id`；因为视觉换行而拆开的行仍属于同一段。
5. 表格网格：记录 `row`、`column`、`row_span`、`col_span`；无法确定时填 `uncertain` 并写说明。
6. 页面和 bbox：使用物理页码及页面坐标，坐标原点注明 `top-left` 或 `bottom-left`。

## 推荐操作顺序

1. 查看 `rendered/` 下的页面 PNG；目前已渲染 `SELF-002`，其他样本可用相同命令补渲染。
2. 先标页眉、页脚和脚注，再标正文标题、段落、表格和参考文献，避免把家具元素混入正文。
3. 对 `SELF-002` 明确记录跨栏标题、左栏/右栏的先后顺序，以及表格是否跨越栏宽。
4. 标注完成后，将结果保存为 `manual-annotations/SELF-00x.json`，不要覆盖 `samples/self-authored/annotations/` 中的固定查询文件。

## JSON 记录模板

```json
{
  "experiment_id": "TECH-DOC-007-R02-text-structure",
  "sample_id": "SELF-002",
  "source_sha256": "从 samples/self-authored/self-authored-manifest.json 复制",
  "annotator": "填写姓名或编号",
  "annotation_version": 1,
  "coordinate_system": "top-left",
  "page_count": 2,
  "units": [
    {
      "unit_id": "SELF-002-p1-u01",
      "physical_page": 1,
      "reading_order_rank": 1,
      "label": "title",
      "text": "页面上看到的原文",
      "bbox": [0, 0, 0, 0],
      "heading_level": 1,
      "paragraph_id": null,
      "table": null,
      "notes": ""
    },
    {
      "unit_id": "SELF-002-p1-u02",
      "physical_page": 1,
      "reading_order_rank": 2,
      "label": "paragraph",
      "text": "页面上看到的原文",
      "bbox": [0, 0, 0, 0],
      "heading_level": null,
      "paragraph_id": "p1-paragraph-01",
      "table": null,
      "notes": ""
    }
  ],
  "table_grids": [],
  "uncertainties": [],
  "review_status": "draft"
}
```

## 样本专属提醒

| 样本 | 必须确认 |
|---|---|
| `SELF-001` | 页眉/页脚是否排除正文；两个标题的级别；表格三行三列；脚注是否独立元素 |
| `SELF-002` | 已重新生成：页面顶部是跨栏标题区，正文按左栏再右栏阅读，表格完整位于左栏。请确认跨栏标题之后是否先读完整左栏，再读右栏；第二页在第一页两栏内容之后 |
| `SELF-003` | 公式是否作为正文、公式对象或图注；表格的三行三列；“合并单元格需保留”是否只是单元格文本而非真实合并 |

## 可由系统自动完成的部分

`automatic-score.json` 已记录固定查询和证据片段命中率。当前三个文本型 PDF 的证据片段命中率均为 `1.0`；这只能说明样本中的关键词仍可找到，不能替代阅读顺序、段落边界、标题层级和表格结构评分。PyMuPDF 的 `DICT/RAWDICT` 原始结果位于 `pymupdf/SELF-*.json`，可用于复制候选 bbox，但复制后必须以页面人工核对。
