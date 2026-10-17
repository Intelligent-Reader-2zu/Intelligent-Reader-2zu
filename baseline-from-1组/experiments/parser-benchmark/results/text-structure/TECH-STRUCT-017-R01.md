# TECH-STRUCT-017-R01 Docling 标题与 PDF 内嵌目录重合度

日期：2026-09-29  
范围：比较 Docling 的 `section_header` 与 PDF 内嵌目录条目，量化标题候选和目录结构的初步重合程度。

## 1. 方法

脚本：`scripts/score_external_docling_toc_overlap.py`  
结果：`external-docling-toc-overlap.json`

对每份 PDF 读取 PyMuPDF 的 `get_toc()`，再读取 Docling 原始导出的 `section_header` 文本。比较时忽略大小写、空白和标点，并使用字符串相似度阈值 `0.86`；因此 `Getting Started` 与 `GettingStarted` 可以被视为同一候选。

## 2. 结果解释

输出同时给出两个方向的重合代理：

- `toc_to_docling_overlap_proxy`：内嵌目录条目中有多少能找到 Docling 标题候选；
- `docling_to_toc_overlap_proxy`：Docling 标题候选中有多少能在内嵌目录找到近似条目。

这两个数不是 Precision/Recall。PDF 内嵌目录可能遗漏正文小节，Docling 也可能把封面、页眉、作者信息或图文块误分类为 `section_header`。

当前代理值：

| 样本 | 内嵌目录条目 | Docling 标题候选 | 目录→Docling | Docling→目录 | 目录层级 | Docling 层级 |
|---|---:|---:|---:|---:|---|---|
| `OPEN-003` | 120 | 149 | 0.9833 | 0.7919 | 1/2/3/4 | 全部 1 |
| `OPEN-010` | 10 | 30 | 1.0000 | 0.3333 | 1/2 | 全部 1 |
| `OPEN-011` | 17 | 21 | 1.0000 | 0.8095 | 1/2 | 全部 1 |

## 3. 重点观察

1. 该实验可以把“目录条目缺失”和“Docling 标题候选过多”分开列出，优先人工查看未匹配项。
2. 词间连接只要字符序列仍相近，就可能被重合代理匹配；因此它只能用于发现候选覆盖，不代表显示文本质量已经合格。
3. Docling 当前导出的 `level` 分布应与 PDF 目录层级分布并列查看，不能直接把所有 `level=1` 当作真实层级。

## 4. 下一步

对未匹配的目录条目和 Docling 候选建立人工标注：区分真实标题、封面元数据、页眉页脚、图注、作者信息和正文小节，再计算标题文本匹配率、层级准确率和父子关系准确率。
