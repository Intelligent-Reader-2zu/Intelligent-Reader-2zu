# TECH-OCR-023-R01 公开 OCR 样本来源与许可记录

> 本记录证明样本获取、版本固定和许可边界已被记录，不代表样本内容可以不受限制地再分发，也不代表任何 OCR 质量结论。

## 获取结果

- 来源仓库：`PaddlePaddle/PaddleOCR`
- 固定提交：`dab3fe35379033fdcb2d0e9572fac0b36c9a9ebf`
- 获取日期：`2026-09-28`
- 仓库许可证：`Apache-2.0`，本地保存为 `samples/public-ocr/PaddleOCR-LICENSE.txt`
- 下载方式：GitHub REST `git/blob` API，按 Git blob SHA 获取 Base64 内容并在本地解码；未关闭 TLS 证书校验。
- 出域标记：全部样本 `cloud_upload_allowed=no`，只用于本地技术实验。

浏览器访问 Wikimedia Commons 和 GitHub 页面时均得到 `ERR_CONNECTION_CLOSED`。随后使用终端访问 GitHub 官方 API；`raw.githubusercontent.com` 的证书链在当前网络环境下不受信任，因此没有用 `--insecure` 绕过，而是改用证书校验成功的 API 域名。

## 纳入样本

| ID | 仓库路径 | SHA-256 | 场景 |
|---|---|---|---|
| `PUB-OCR-001` | `tests/test_files/book.jpg` | `782cc71a...dcbcc4` | 英文实拍双页、背景干扰、页码、算式 |
| `PUB-OCR-002` | `tests/test_files/book_rot180.jpg` | `6fb6b8ea...f4e534` | 同页 180 度旋转 |
| `PUB-OCR-003` | `tests/test_files/doc_with_formula.png` | `6b07d285...9f26e80` | 英文双栏、公式、特殊符号、打印页码 |
| `PUB-OCR-004` | `tests/test_files/medal_table.png` | `6d50148c...e88fa8` | 中文、英文缩写、数字、有边框表格 |
| `PUB-OCR-005` | `tests/test_files/seal.png` | `be29cb91...a6c24` | 中文红章、弧形文字、背景文字、编号 |
| `PUB-OCR-006` | `tests/test_files/table.jpg` | `acd113bb...3115c` | 小尺寸中英混排表格 |
| `PUB-OCR-007/008` | `工作区/datasets/images/ch_doc1.jpg` / `ch_doc3.jpg` | 见 `manifest.json` | 低高度中文与数字混排短行 |
| `PUB-OCR-CTRL-001` | `langchain-paddleocr/tests/data/sample_pdf.pdf` | `8823befb...181789` | 4 页文本层负控，应跳过 OCR |

完整 blob SHA、文件 SHA-256、尺寸、特征和源路径见 `samples/public-ocr/manifest.json`。

## 许可边界

仓库声明 Apache-2.0，但部分示例可能源自第三方数据集。当前记录没有证明仓库许可证自动解决所有上游图片权利，因此结论是：

- 可用于本项目的本地、不可出域技术验证；
- 不应把这些样本直接打包进产品、公开基准包或对外演示材料；
- 如需再分发，必须继续核验每个上游数据集的来源和许可证。

## 排除样本

XFUN/FUNSD、CDLA 和若干文档候选带有烧录的彩色标注框，部分表单还包含个人样式字段；这些文件已下载用于视觉筛选，但不进入质量评分。排除清单和原因已写入 `manifest.json`，避免把标注文字当作 OCR 输入质量或把公开表单内容发送云端。

结论：`可用于本地受限实验`。许可信息足以支撑本轮技术验证，但不足以支撑产品内再分发。
