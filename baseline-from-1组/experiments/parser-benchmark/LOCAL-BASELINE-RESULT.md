# Local Parser Baseline Result

> 实验编号：`TECH-DOC-001-R01-local-baseline`
>
> 日期：2026-09-24
>
> 范围：项目组自制样本 `SELF-001`、`SELF-002`、`SELF-003`、`SELF-004`、`SELF-005`、`SELF-008`、`SELF-010`、`SELF-011`

## 1. 环境

| 项目 | 结果 |
|---|---|
| Java | 21.0.8（Maven 使用的运行时） |
| Maven | 3.9.11 |
| Python | 3.13.2 |
| PyMuPDF | 1.25.3 |
| python-docx | 1.1.2 |
| markdown-it-py | 4.2.0 |
| pdfplumber | 未安装 |
| Docling | 未安装 |
| Unstructured | 未安装 |
| OCR 适配器 | 未接入 |
| 云端服务 | 未调用 |

原始 JSON 结果位于 `results/local-baseline/`，运行脚本为 `scripts/run_local_baseline.py`。每个样本均记录源文件 SHA-256；脚本以 `-B` 运行，避免产生 Python 缓存文件。

## 2. 观测结果（F）

- PyMuPDF 对 `SELF-001`、`SELF-002`、`SELF-003` 的文本层能够返回物理页号、文本块数量和块坐标样例。
- `SELF-002` 双栏样本和 `SELF-003` 表格/公式样本均能返回文本，但本轮没有计算人工参考级阅读顺序、标题层级 F1 或表格结构准确率。
- `SELF-004` 扫描 PDF 返回 2 个物理页、每页 1 个图像、0 个文本块；本轮 OCR 状态为 `not_run`，固定查询均未命中。
- python-docx 能读取 `SELF-005` 的段落样式、12 个段落和 1 个表格；结果明确记录视觉页码不可由该库直接获得。
- markdown-it-py CommonMark 模式能识别 `SELF-008` 的 4 个标题和源行区间；GFM 扩展在本轮未启用，不能据此证明脚注、数学公式或表格扩展兼容。
- 显式编码基线能读取 `SELF-010` UTF-8 和 `SELF-011` GB18030；GB18030 样本先触发 UTF-8 解码错误，再按实验规则回退。

## 3. 工程解释（I）

- 文本型 PDF 的“能提取文本”与“阅读顺序、标题层级和表格结构正确”是不同指标；当前结果只证明前者的可观察性和页级/bbox 字段可保存。
- 扫描 PDF 在没有 OCR 适配器时应进入可见的降级状态，不能把空文本当作解析成功。
- DOCX 的段落样式和表格可以进入实验 IR，但视觉分页需要另行渲染或定位策略。
- Markdown 需要把 CommonMark 核心能力与 GFM/脚注/数学公式扩展分开验证。

## 4. 阶段性结论（C，非最终选型）

本轮只完成本地基线，不足以比较七类候选工具的质量，也不能形成一期最终支持范围。当前可进入下一轮的顺序是：

1. 为 PyMuPDF 增加结构化 `DICT/RAWDICT` 和人工参考对照；
2. 接入 OCR 工具后重跑 `SELF-004`，记录 CER/WER、置信度和原页回溯；
3. 安装并固定 pdfplumber、Docling、Unstructured 版本后与同一批样本对比；
4. 为 Markdown 增加 GFM/脚注/数学公式扩展的独立对照；
5. 不把当前结果写成“支持扫描 PDF”或“表格/公式可靠问答”。

## 5. 已知风险（R）

- 当前 Windows 环境存在中文输出编码显示异常的迹象，实验结果文件本身使用 UTF-8 保存；后续应在结果 JSON 中继续保留源哈希和工具版本。
- `SELF-005` 的查询命中不等于脚注、分页和视觉页码都已正确保留；需要检查 OOXML relationships 和渲染结果。
- 云端服务尚未执行，任何云端准确率、费用和版本漂移结论均待验证。
