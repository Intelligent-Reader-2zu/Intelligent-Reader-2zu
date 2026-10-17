# TECH-STRUCT-011-R01 外部样本盘点与结构覆盖

日期：2026-09-29  
范围：对工作区已有外部 PDF/HTML 样本执行来源清单、哈希和廉价结构信号核验。

## 1. 目的

此前外部样本已经下载到 `samples/external-candidates`、`samples/external-replacements` 和 `samples/open-authored-substitutes`，但它们尚未进入可复现的实验输入核验。本轮不直接把外部材料当作金标准，而是先确认：

- 文件仍存在，且与清单 SHA-256 一致；
- PDF 是否有文本层、页数、目录、图片和页级块；
- HTML 是否有标题层级、表格、代码、链接、导航和脚本噪声；
- 每份材料的来源、预期版面特征和许可备注是否随结果保留。

脚本：`scripts/inventory_external_samples.py`  
机器结果：`results/text-structure/external-inventory.json`

## 2. 样本来源

| 清单 | 内容 |
|---|---|
| `external-candidate-manifest.json` | NIST、W3C、RFC、OpenStax、arXiv PDF/HTML 候选 |
| `external-replacement-manifest.json` | W3C、OWASP、RFC、NIST 替代材料 |
| `auth-substitute-manifest.json` | NIST PDF 与 W3C HTML 的开放材料替代样本 |

本轮没有新增网络下载；复用了工作区已有下载文件。所有条目的 `cloud_upload_allowed` 仍按清单保留为 `unknown`，不把“可公开访问”解释成可任意再分发或上传。

## 3. 核验结果

运行结果应以 `external-inventory.json` 为准，重点检查：

- `status=ok`：文件存在且 SHA-256 与清单一致；
- `status=hash_mismatch`：不能进入后续对照实验，需重新下载或更新清单；
- `status=inspection_failed`：文件存在但基础解析失败，保留为失败样本；
- PDF `toc_entry_count` 仅表示 PDF 内嵌目录条目数，不等于标题识别准确率；
- HTML `heading_levels` 仅表示 DOM 标签分布，不等于正文标题树已经去除导航和脚本噪声。

## 4. 如何进入下一轮结构实验

建议从核验通过的样本中分层抽取：

1. 双栏论文 PDF：`docling-technical-report.pdf`、`layoutlmv3.pdf`，观察阅读顺序、图表、公式和参考文献。
2. 长篇技术报告 PDF：NIST 系列，观察目录、页眉页脚、表格、附录和跨页结构。
3. 规范型网页：W3C、RFC 和 OWASP，观察标题树、锚点、代码块、导航与引用关系。
4. 教材型网页：OpenStax，观察图注、混合内容、章节导航和正文噪声。

下一轮应把选定样本复制到一个明确的实验输入清单，并为每份建立人工最小金标准；只有完成标注后，才能报告标题 F1、阅读顺序、表格结构或引用定位准确率。

## 5. 边界

本实验不是许可审查、结构准确率、OCR 评测或问答评测。尤其不能把 PDF 内嵌目录数量、HTML `h1`-`h6` 数量或文件存在性直接当作结构识别成功。原始下载文件仅用于本地实验，除非后续逐项确认许可和上传政策，否则不应上传到云服务。
