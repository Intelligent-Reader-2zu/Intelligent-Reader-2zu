# TECH-QA-016-R01 本地大模型环境门禁

本记录只判断本机是否具备安全开始本地生成模型试验的条件，不下载权重、不安装运行时，也不评价模型质量。

内存：15.73 GiB，总可用：3.7 GiB；D 盘可用：21.37 GiB；GPU：NVIDIA GeForce RTX 2050 / 4096 MiB；PyTorch CUDA：不可用。

轻量路径：**conditional_not_ready**；高质量路径：**not_feasible_on_current_device**。

## 观察

- 4GB GPU can only be considered for small quantized models or partial offload
- current PyTorch is CPU-only; CUDA inference is unavailable
- no local generation runtime is installed
- no local generative model weights are present
- current available memory is below the 8 GiB trial headroom target

## 结论

当前机器只能把 4B/8B 量化模型作为释放内存、准备运行时后的条件候选；不应在当前状态直接下载大权重或承诺交互式质量。14B/32B 高质量路径不适合作为本机实验目标。

安全下一步：释放内存或换到更大设备，固定一个本地运行时和 4B/8B 量化权重，先跑离线短文档和 15 题固定集；文档不出本机。
