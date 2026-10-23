# TECH-STRUCT-016-R01 外部 PDF 的 Docling 结构基线

日期：2026-09-29  
范围：使用工作区已有的隔离环境 `.venv-parser` 和 Docling 2.130.0，对两份外部双栏论文 PDF 执行文本层结构解析。

## 1. 环境核验

已确认：

- `experiments/parser-benchmark/.venv-parser/Scripts/python.exe` 存在；
- Python `3.13.2`；
- Docling `2.130.0` 已安装；
- `pip show docling` 显示其位于隔离环境，不属于系统 Python；
- 本轮没有重复安装依赖，也没有修改生产依赖文件；
- 使用 ASCII 路径 `D:\docling-cache` 保存临时文件和模型缓存，避免此前记录的 Windows `Illegal byte sequence` 问题。

## 2. 运行配置

| 选项 | 值 |
|---|---|
| `do_ocr` | `false`，显式关闭 |
| `do_table_structure` | `true` |
| `do_formula_enrichment` | `false` |
| 页面/图片生成 | `false` |
| 样本 | `OPEN-010` Docling Technical Report；`OPEN-011` LayoutLMv3 |

原始导出位于 `results/text-structure/external-docling/`，机器摘要为 `external-docling/summary.json`。

## 3. 结果

| 样本 | 页数 | 文本对象 | `section_header` | 表格 | 单元格 | 图片 | 公式 | 脚注 | 图注 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `OPEN-003` | 80 | 1071 | 149 | 19 | 656 | 12 | 0 | 0 | 6 |
| `OPEN-010` | 9 | 739 | 30 | 3 | 36 | 5 | 0 | 1 | 7 |
| `OPEN-011` | 10 | 292 | 21 | 4 | 382 | 5 | 3 | 0 | 11 |

三份样本均成功完成转换；`OPEN-010/011` 单份耗时约 20.2 秒，`OPEN-003` 约 90.2 秒。Docling 对文本层、页面、图、表格和部分特殊元素提供了结构对象；`OPEN-011` 能输出 `formula`，而 `OPEN-003/010` 的公式没有被标为独立公式对象。

## 4. 关键观察

1. `OPEN-010` 的标题文本出现 `GettingStarted`、`Processingpipeline`、`AImodels` 等词间连接，说明即使 `section_header` 分类成功，文本归一化和标题显示文本仍需校正。
2. `OPEN-010` 的 30 个 `section_header` 全部由当前导出标成 `level=1`，不能直接解释为完整标题层级；需要结合编号、目录和视觉样式重建层级。
3. `OPEN-011` 的双栏论文得到 21 个标题、4 个表格、382 个单元格、3 个公式和 11 个图注，但这些数量不代表阅读顺序、表格对齐或公式语义正确。
4. `OPEN-003` 有 230 个页眉和 78 个页脚对象，但没有独立脚注对象；`OPEN-010` 有页眉、页脚和脚注对象，`OPEN-011` 有页眉但没有脚注对象。这组结果覆盖了家具元素和脚注缺失的对照场景。

## 5. 对统一 IR 的映射建议

- 保留 Docling 原始 `label`，另映射到 `element_type`，不要把 `section_header` 直接当成最终 `heading`；
- 从 `prov.page_no + bbox + charspan` 生成位置证据，并保留 `coord_origin`；
- 公式使用 `element_type=equation`，同时记录 `verified=false`，除非后续有公式金标准；
- 表格保留 `table -> cell` 子树和 `row_span/col_span`，表格文本顺序须经过人工抽样；
- 页眉/页脚/脚注/图注保留独立角色，不能静默并入正文；
- 标题层级必须由视觉/编号/目录综合校正，不能复用 Docling 当前全为 `level=1` 的结果。

## 6. 边界和下一步

本轮是外部结构 smoke test，不包含人工金标准、阅读顺序准确率、标题 F1、表格 cell 对齐、脚注召回率、公式语义准确率或问答评测。下一步应针对 `OPEN-010` 第 1/3/7 页和 `OPEN-011` 第 1/3 页，将 Docling 输出与渲染页面标注逐元素对照。
