# TECH-STRUCT-007-R01 网页 DOM 结构基线

日期：2026-09-29  
样本：`SELF-012-noisy.html`，项目组自制静态网页快照。

## 1. 结果

使用 BeautifulSoup 建立以 `<article>` 为根的保守 DOM IR：

| 元素 | 数量 |
|---|---:|
| heading | 2 |
| paragraph | 2 |
| table | 1 |
| table_cell | 6 |
| code_block | 1 |
| nav/aside/script/style 噪声 | 4 |
| footer | 1 |

标题、`id="method"` 锚点、正文段落、表格、代码块和表格单元格均被保留；导航、广告、脚本和样式没有进入 article 正文元素。原始结果见 [`ir/SELF-012.html.json`](ir/SELF-012.html.json)。

## 2. 结论边界

- 静态 HTML 的 DOM 结构比 PDF 的视觉推断更直接，标题层级来自 `h1..h6`，表格来自 DOM 行列，链接锚点可保存为 `source_selector` 或 `id`。
- 这不是网页正文抽取的完整方案：SPA 动态渲染、shadow DOM、iframe、重复移动端 DOM 和广告注入尚未测试。
- 生产实现应保存 URL、抓取时间、渲染快照、DOM selector/anchor；正文清理失败时回退到原始 DOM，而不是静默删除内容。

## 3. 对项目的影响

网页材料可提供较稳定的目录导航和行/DOM 引用，但需要把正文候选与噪声元素分层保存。网页与 PDF/DOCX 不能共用“页码”字段，建议统一使用 `location` 联合类型：`pdf_page_bbox`、`docx_paragraph`、`markdown_line`、`html_selector`。
