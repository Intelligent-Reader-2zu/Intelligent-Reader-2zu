# 人工标注结果目录

`SELF-001.json`、`SELF-002.json`、`SELF-003.json` 已由用户通过自然语言逐项确认，并由实验脚本原始坐标回填 bbox。每个文件保留确认方式、原始回答、确认项目和源文件 SHA-256；模板见上级目录的 `MANUAL-ANNOTATION-TEMPLATE.md`。

修改或替换样本后必须重新确认标注。`score_manual_structure.py` 会在评分前校验标注与解析结果的源文件哈希，哈希不一致时终止评分。
