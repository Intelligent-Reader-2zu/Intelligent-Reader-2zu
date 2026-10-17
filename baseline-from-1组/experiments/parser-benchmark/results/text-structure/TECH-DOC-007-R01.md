# TECH-DOC-007-R01 文本结构解析实验结果

日期：2026-09-24  
范围：本地、授权自制样本；不执行 OCR、不调用云服务、不评估检索或问答质量。

## 1. 实验对象

| 样本 | 格式 | 本轮处理 |
|---|---|---|
| `SELF-001` 至 `SELF-003` | 文本型 PDF | PyMuPDF、pdfplumber、Docling 无 OCR、Apache Tika |
| `SELF-004` | 扫描型 PDF | 仅确认无文本层；不评分，不执行 OCR |
| `SELF-005` 至 `SELF-007` | DOCX | python-docx 基线、Apache Tika |
| `SELF-008` 至 `SELF-009` | Markdown | CommonMark 基线、Apache Tika |
| `SELF-010` 至 `SELF-011` | TXT | 显式编码基线、Apache Tika |

原始输入哈希、运行参数和结果见本目录下各 `SELF-*.json`、`docling/` 和 `tika/`。统一实验编号为 `TECH-DOC-007-R01-text-structure`。

## 2. 结果摘要

### PDF

- PyMuPDF 和 pdfplumber 均能返回文本型 PDF 的物理页、文本和坐标相关信息；PyMuPDF 结果包含 block/word 坐标，pdfplumber 结果包含字符/单词和表格候选数量。
- Docling 在 `do_ocr=False`、`do_table_structure=True` 下成功输出 `SELF-001` 至 `SELF-003` 的文档树、页数、文本元素和表格对象。
- Apache Tika 能提取正文和 PDF 元数据，但本实验输出没有 bbox、标题层级或细粒度布局字段。
- `SELF-002` 双栏样本仍存在阅读顺序、词间空格和表格线性化风险；本轮没有人工参考标注，因此不报告结构正确率。
- 初版 `SELF-002` 曾存在表格越界且正文未进入右栏的样本缺陷；已在 `TECH-DOC-007-R02` 重新生成。新版页面使用跨栏标题区、独立左右正文栏和栏内表格，必须以新版 SHA-256 和 R02 结果为准。
- `SELF-004` 两页均无文本层，状态仅为 `out_of_scope_no_text_layer`；这不是 OCR 失败率，也不能推导 OCR 质量。

### DOCX、Markdown、TXT

- python-docx 能保留段落顺序、Heading 样式和表格网格，但不直接给出稳定的视觉页码。
- CommonMark 解析能保留 Markdown 标题层级和源代码行区间；GFM 表格、脚注和数学公式扩展未在本轮启用。
- 显式 UTF-8 -> GB18030 回退基线能读取两个 TXT 样本。Apache Tika 对 UTF-8 TXT 成功，但对 GB18030 样本走 `EmptyParser`，现标记为 `limited_no_text`，不是普通成功。
- Tika 对 DOCX 能返回正文、页眉页脚、脚注引用和表格线性文本，但不能替代 DOCX 样式/表格专用解析器。

## 3. 对后续链路的意义

本轮只证明候选工具能够产出可保存的原始结果，不能证明自然阅读顺序、标题层级、段落边界或表格结构达到产品阈值。后续检索、问答和引用定位至少应保留：源文件哈希、解析器版本和配置哈希、元素 ID、元素类型、文本、物理页、bbox（可用时）、标题路径（可用时）以及原始输出引用。

Tika 的 Java 原生对照适合做格式识别和纯文本/元数据兜底，但其结果不足以单独承担需要 bbox、阅读顺序或结构化表格的引用链路。`SELF-011` 暴露了编码兼容风险：一期若支持 GB18030，不能仅依赖默认 Tika 自动识别。

## 4. 本轮边界和未完成指标

- 未进行 OCR，因此没有 CER/WER、OCR 置信度或扫描 PDF 质量结论。
- 未完成正文字符召回、阅读顺序、标题层级、段落边界、表格单元格结构和 bbox 引用准确率评分。
- 未完成 DOCX 页眉/页脚/脚注的结构化对比，以及 Markdown GFM/脚注/数学扩展对比。
- 未进行云服务、费用、区域或数据驻留实验。

## 5. 可记录验证项

| 编号 | 验证项 | 当前状态 |
|---|---|---|
| `TECH-DOC-007-R01-V01` | 文本型 PDF 是否能保留文本和物理页 | 已观察到可行，尚无召回阈值评分 |
| `TECH-DOC-007-R01-V02` | 双栏 PDF 阅读顺序和段落边界 | 风险，待人工标注评分 |
| `TECH-DOC-007-R01-V03` | 无 OCR 时扫描 PDF 的可识别边界 | 已确认无文本层，OCR 延后 |
| `TECH-DOC-007-R01-V04` | DOCX 样式/表格与视觉页码分离 | 已观察到逻辑结构可读，视觉页码待验证 |
| `TECH-DOC-007-R01-V05` | Markdown CommonMark 结构和源行定位 | 基线可行，GFM 扩展待验证 |
| `TECH-DOC-007-R01-V06` | GB18030 TXT 的本地编码回退 | 显式回退可行，Tika 默认路径受限 |
| `TECH-DOC-007-R01-V07` | Java Tika 输出能否满足 bbox/标题路径引用 | 当前不能，需保留其他解析器对照 |

## 6. 阶段判断

文本型单栏 PDF、DOCX、Markdown 和 TXT 仍适合作为一期优先验证范围；双栏、复杂表格、公式和视觉页码应保持受限支持。扫描 PDF 在本轮只登记为无文本层输入，不能据此进入一期 OCR 承诺。当前证据不足以进行候选工具最终选型。
