# TECH-OCR-019-R01 EasyOCR 本地环境与模型获取验证

> 本记录没有产生 OCR 文本，不能用于评价 EasyOCR 的中英文识别质量。

- Python：`3.11.16`；EasyOCR：`1.7.2`；PyTorch：`2.14.0+cpu`
- PyTorch CPU 张量运算、torchvision 和 EasyOCR 导入均成功；独立环境未复现共享环境的 `shm.dll` 错误。
- 计划语言：`ch_sim + en`；模型缓存固定到项目 ASCII 路径。
- 样本 SHA-256：`ab008a1879ed22c5f92abe0dab30f1bbd2ffe2e462b1b2c25ec55cc7fa03fa63`，但未进入推理阶段。

## 阻塞

EasyOCR 通过 `urllib` 获取检测模型时，默认 Python CA 和注入 Windows 系统证书的 `truststore` 均拒绝当前下载端点的证书链：链终止于不受信任的根证书。实验没有关闭 TLS 校验，也没有使用跳过证书检查的下载方式。

当前结论是“运行时可安装，模型获取受网络证书策略阻塞”，不是算法质量失败。后续可由受信任制品库提供经哈希校验的 EasyOCR 模型并放入缓存，再使用现有脚本继续同口径 CER/WER/bbox/时延实验。

原始结果：`result.json`；脚本：`scripts/run_ocr_easyocr.py`；依赖：`requirements-easyocr311.txt`。
