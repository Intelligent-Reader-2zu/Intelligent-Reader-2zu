# TECH-OCR-016-R01 PaddleOCR 本地兼容性实验

> 本记录只说明当前 Windows/Python 环境能否启动候选，不代表 PaddleOCR 的识别质量或最终选型。

- 样本：`SELF-004` 两页，SHA-256 `ab008a1879ed22c5f92abe0dab30f1bbd2ffe2e462b1b2c25ec55cc7fa03fa63`
- 运行时：Windows，Python `3.13.2`，CPU
- PaddleOCR：`2.10.0`；PaddlePaddle：`3.3.1`
- 模型：PP-OCRv4 中文检测/识别 + mobile 方向分类器；模型缓存已放在项目 ASCII 路径，绕过 Windows 中文用户目录路径问题
- 模型下载和初始化成功，初始化约 `554.55 ms`（不含首次下载）

## 结果

| 页面 | 状态 | 错误 |
|---|---|---|
| 1 | 失败 | `OneDnnContext does not have the input Filter`，`fused_conv2d` |
| 2 | 失败 | `OneDnnContext does not have the input Filter`，`fused_conv2d` |

未产生可评分的文本、bbox、置信度、CER/WER 或时延；不能据此评价中文、英文、混排、表格或版面能力。

## 解释与下一步

1. 这是当前 PaddleOCR 2.10 静态模型与 PaddlePaddle 3.3.1 推理后端的兼容性阻塞；当前 PyPI 在 Python 3.13/Windows 可见的 PaddlePaddle 版本只有 3.x，不能直接用 2.x wheel 修复。
2. 旧版在中文用户目录下还暴露了模型路径乱码问题，已通过 `PADDLE_OCR_BASE_DIR` 固定到 ASCII 项目目录解决；该修复应保留在复现实验脚本中。
3. 后续若要继续，应使用独立 Python 3.10/3.11 环境锁定 PaddleOCR/PaddlePaddle 官方兼容矩阵，或改测 PaddleOCR 3.x 并隔离 `modelscope/torch` 依赖。两条路径都应重新下载模型并重跑同一金标准。

原始输出摘要：`result-R01.json`；脚本：`scripts/run_ocr_paddleocr_legacy.py`。后续兼容环境复测使用 `R02`，不覆盖本记录。
