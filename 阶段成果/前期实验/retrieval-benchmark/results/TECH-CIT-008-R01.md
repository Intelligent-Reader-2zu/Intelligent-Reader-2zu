# TECH-CIT-008-R01 OCR/表格低置信度引用降级

| 退化变体 | 关键字符串最小召回 | 最大 CER | 引用动作 |
|---|---:|---:|---|
| `base300` | 0.667 | 0.102 | `page_image_warning` |
| `downsample150` | 0.667 | 0.108 | `page_image_warning` |
| `blur` | 0.667 | 0.120 | `page_image_warning` |
| `low_contrast_noise` | 0.667 | 0.108 | `page_image_warning` |
| `rotate3` | 1.000 | 0.054 | `page_image_warning` |

结论：即使关键字符串召回为 1，只要 CER 非零，精确数值/公式回答仍进入页面图像+警告降级；关键词命中不能替代字符级正确性。
