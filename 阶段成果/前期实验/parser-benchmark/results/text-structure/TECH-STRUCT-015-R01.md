# TECH-STRUCT-015-R01 外部 PDF/HTML 保守基线 IR

日期：2026-09-29  
范围：将 3 份代表 PDF 和 3 份网页快照映射为实验 IR，观察位置字段、标题候选和 DOM 定位字段的完整性。

## 1. 方法

脚本：`scripts/build_external_baseline_ir.py`  
输出目录：`results/text-structure/external-ir/`

PDF 使用 PyMuPDF 行级文本和 bbox。标题只按字号、粗体、文本长度生成 `heading_candidate`，不写入最终 `heading_level`。HTML 保留所有 `h1`-`h6` DOM 标题、唯一 selector，并额外标记是否位于 `article/main` 容器。

## 2. 结果

| 样本 | 元素数 | 标题候选/DOM 标题 | 页数 | bbox 完整率 | article/main 标题 | selector 完整率 |
|---|---:|---:|---:|---:|---:|---:|
| `OPEN-003` PDF | 3389 | 420 候选 | 80 | 1.00 | N/A | N/A |
| `OPEN-010` PDF | 1279 | 424 候选 | 9 | 1.00 | N/A | N/A |
| `OPEN-011` PDF | 1415 | 225 候选 | 10 | 1.00 | N/A | N/A |
| `WEB-001` HTML | 230 | 230 DOM 标题 | N/A | N/A | 219 | 1.00 |
| `WEB-002` HTML | 311 | 311 DOM 标题 | N/A | N/A | 0 | 1.00 |
| `WEB-004` HTML | 7 | 7 DOM 标题 | N/A | N/A | 2 | 1.00 |

## 3. 解释

1. PDF 的物理页码和 bbox 字段可以稳定进入 IR，但标题候选远多于真实标题，必须继续依赖版面模型、字体样式、编号模式和人工金标准；不能把 `heading_candidate` 直接用于目录。
2. HTML selector 在 3 份样本中均唯一且完整，适合引用回溯；但 `WEB-002` 没有 `article/main` 语义容器，article-only 抽取会错误地认为正文标题为 0。
3. `WEB-001` 的 219 个标题位于 `article/main`，仍有 11 个标题在语义容器外，说明导航/附录/生成块不能只用一个容器规则处理。
4. `WEB-004` 只有 2 个标题位于 `article/main`，需要同时保留 DOM 标题和正文候选，以免教材网页章节导航或动态组件造成漏项。

## 4. 产品含义

- PDF：先返回候选标题和低置信度提示；只有经过结构模型或人工校验的标题才能进入正式目录。
- HTML：保留 `dom_heading`、`navigation_candidate` 和 `article_candidate` 的角色差异；当没有 `article/main` 时，降级到正文清理规则、标题邻域和快照 selector，而不是返回空正文。
- 所有元素继续保留 `source_hash`、`element_id`、`physical_page/bbox` 或 `source_selector`，让检索和引用可以回到原始材料。

## 5. 边界

本实验只报告字段完整性和保守候选，不报告标题 F1、阅读顺序、网页正文 Precision/Recall、表格结构或问答准确率。机器结果见 `external-ir/summary.json` 及各样本 JSON。
