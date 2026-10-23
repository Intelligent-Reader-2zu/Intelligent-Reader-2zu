# TECH-STRUCT-001-R01 逻辑结构最小实验

日期：2026-09-29  
范围：DOCX、Markdown、TXT 的逻辑结构基线；不执行 OCR，不评估最终视觉分页、检索、问答或引用质量。

## 1. 实验目的

验证三类低风险输入能否稳定输出标题、段落、表格、编码和源位置等结构字段，并确认这些结果可以进入后续统一 JSON IR。实验复用了项目组自制样本和现有 `run_text_structure_experiment.py`，没有引入新的生产依赖。

## 2. 环境和样本

| 项目 | 结果 |
|---|---|
| Python | 3.13.2 |
| DOCX 解析器 | `python-docx 1.1.2` |
| Markdown 解析器 | `markdown-it-py 4.2.0`，CommonMark 模式 |
| TXT 基线 | UTF-8 解码失败后回退 GB18030 |
| OCR | 未启用 |
| 样本 | `SELF-005` 至 `SELF-011` |

## 3. 结果

| 样本 | 格式 | 观察到的结构字段 | 结果 |
|---|---|---|---|
| `SELF-005` | DOCX | 12 个段落、5 个标题、1 个 3×3 表格；标题样式包含 `Title`、`Heading 1/2` | 逻辑结构读取成功 |
| `SELF-006` | DOCX | 10 个段落、4 个标题、1 个 3×4 表格；列表内容仍表现为普通段落文本 | 逻辑结构读取成功，列表语义尚未评分 |
| `SELF-007` | DOCX | 12 个段落、5 个标题、1 个 4×4 表格；中英文混排和显式分页可读 | 逻辑结构读取成功 |
| `SELF-008` | Markdown | 38 行、66 个 token、4 个标题；CommonMark 标题和行号映射可读 | 基线成功；GFM/脚注/数学扩展未启用 |
| `SELF-009` | Markdown | 17 行、4 个标题，保留 `H2 -> H4 -> H3` 跳级 | 基线成功；没有静默修正层级 |
| `SELF-010` | TXT | UTF-8、6 行、3 个空行分段、CRLF | 编码和空行边界读取成功 |
| `SELF-011` | TXT | 首次 UTF-8 解码失败，回退 GB18030、2 行 | 编码回退成功 |

## 4. 重要边界

1. `python-docx` 能读出段落样式和表格，但不能从逻辑 XML 直接提供稳定的最终视觉页码；脚注、文本框、列表编号和分页后的视觉关系仍需独立验证。
2. Markdown CommonMark 能识别标题和源行范围，但本次没有启用 GFM 表格、脚注和数学公式插件，因此不能据此宣布扩展语法支持。
3. TXT 只有编码、换行和空行等物理边界，没有天然标题或语义段落；本次的“段落”只是连续非空行分组。
4. 终端输出可能因 Windows 控制台编码显示为乱码，但写入的 JSON 文件使用 UTF-8 且已检查为正确中文内容；这不是解析失败。
5. 当前结果是字段可观察性检查，不是结构正确性验收；还没有人工金标准，因此不报告标题 F1、段落边界 F1 或表格结构准确率。

## 5. 对统一 IR 的映射

本轮可直接映射：

```text
element_type       = title / paragraph / table / table_cell
heading_level      = DOCX Heading 1..9 或 Markdown h1..h6
source_line_start  = Markdown token.map；TXT 行号可补充
source_line_end    = Markdown token.map；DOCX 使用段落序号替代
parent_element_id  = 根据标题栈生成
text               = 原始元素文本
```

本轮仍缺失或不稳定：

```text
physical_page / printed_page_label
bbox
footnote marker -> footnote relation
figure/caption asset relation
stable list item semantics
formula representation
```

因此，当前结果适合验证 `heading_path`、段落/表格块和字符偏移的接口形状，不应直接替换现有 `DocumentBlock` 的生产模型。

## 6. 下一步

1. 为 `SELF-005` 至 `SELF-011` 增加人工标注：标题层级、段落边界、列表项、表格单元格、脚注和分页关系。
2. 固定 Markdown 方言，分别测试 CommonMark、GFM 表格、脚注和数学公式插件。
3. 对 DOCX 使用固定渲染器生成 PDF/页面图，比较逻辑段落与视觉页码、页眉页脚和脚注位置。
4. 把本轮输出映射到结构识别 JSON IR，再与 PDF 的 PyMuPDF/Docling 结果执行同一套字段完整率和下游定位检查。

原始结果：`SELF-005.json` 至 `SELF-011.json`，位于本目录；运行脚本为 `scripts/run_text_structure_experiment.py`。
