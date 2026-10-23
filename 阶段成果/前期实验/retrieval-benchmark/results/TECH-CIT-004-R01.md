# TECH-CIT-004-R01 PDF/OCR bbox 坐标与高亮变换

| 用例 | OCR 词数 | bbox 有效率 | 坐标系 | 旋转 | 缩放 | 状态 |
|---|---:|---:|---|---:|---:|---|
| `base300-p1` | 97 | 1.000 | image_top_left_xywh | 0.0° | 1.5x | PASS |
| `base300-p2` | 88 | 1.000 | image_top_left_xywh | 0.0° | 1.5x | PASS |
| `rotate3-p1` | 94 | 1.000 | image_top_left_xywh | 3.0° | 1.5x | PASS |
| `rotate3-p2` | 94 | 1.000 | image_top_left_xywh | 3.0° | 1.5x | PASS |

## PDF IR 到渲染像素的边界检查

| 样本 | 检查框数 | PDF 坐标有效率 | 渲染像素有效率 |
|---|---:|---:|---:|
| `SELF-001` | 10 | 1.000 | 1.000 |
| `SELF-002` | 24 | 1.000 | 1.000 |
| `SELF-003` | 10 | 1.000 | 1.000 |

结论：现有 OCR 词框可在统一 image-top-left/xywh 坐标系内转换；PDF IR bbox 也能映射到渲染像素边界。该轮没有人工词级金标准，因此不能宣称高亮 IoU 已通过。
