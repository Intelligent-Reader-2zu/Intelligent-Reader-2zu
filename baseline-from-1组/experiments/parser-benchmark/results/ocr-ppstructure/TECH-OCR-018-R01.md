# TECH-OCR-018-R01 PP-StructureV2 本地布局/表格 smoke test

> 本实验只有 4 页项目自制页面图，没有人工布局和单元格金标准。结果是可运行性与失败模式观察，不是结构准确率结论。

- Python：`3.11.16`；PaddlePaddle：`2.6.2`；PaddleOCR：`2.10.0`
- 样本：`SELF-004` 两页扫描图；`SELF-002` 两页双栏/表格渲染图
- 可运行配置：`layout=True, table=False, formula=False, ocr=True`
- 布局-only 初始化约 `2936.62 ms`

| 页面 | 时延 ms | 区域类型 | 观察 |
|---|---:|---|---|
| SELF-004 第 1 页 | 1357.49 | `figure: 1` | 整页被归类为 figure，内部仍返回 9 行 OCR |
| SELF-004 第 2 页 | 1235.55 | `figure: 1` | 倾斜扫描页同样整页归为 figure，内部返回 9 行 OCR |
| SELF-002 第 1 页 | 2121.11 | `text:5, title:4, table:1, footer:2, reference:1` | 双栏区域和表格 bbox 可见；返回顺序并非稳定阅读顺序 |
| SELF-002 第 2 页 | 657.23 | `text:1, footer:2` | 正文和左右页脚分区成功 |

## 表格模块阻塞

完整配置 `table=True` 在初始化表格模型时失败：PaddleOCR 2.10 下载的中文 SLANet 模型路径包含 `paddle3.0b2`，与当前 PaddlePaddle 2.6.2 组合触发 `Tensor's dimension is out of bound` / `scale` 算子错误。表格区域检测仍可在 layout-only 模式出现，但 `res` 为空，未生成 HTML、单元格或行列结构。

这属于子模型/运行时兼容性阻塞，不能据此判断 SLANet 的表格准确率。后续应使用匹配 Paddle 3.x 的独立环境，或固定更旧且明确兼容 Paddle 2.6 的 PP-Structure 模型组合。

## 项目结论

- 当前版本组合可提供布局区域 bbox 和区域内 OCR，但扫描页类别和阅读顺序不足以直接用于可靠引用。
- 对双栏页，必须根据 bbox/栏 ID 重排，不应按返回数组顺序拼接正文。
- 对表格，只能保留检测框、原图裁剪和普通 OCR；在表格模型通过单元格金标准前，不支持结构化表格问答。

原始结果：`result.json` 和逐页 JSON；脚本：`scripts/run_ppstructure_v2.py`。
