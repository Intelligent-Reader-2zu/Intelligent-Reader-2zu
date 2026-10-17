# TECH-STRUCT-013-R01 外部样本人工标注队列

日期：2026-09-29  
范围：为外部代表样本生成不含预测标签的人工标注范围。

## 1. 目的

`TECH-STRUCT-011/012` 已确认文件完整性并提供版面风险信号，但还不能计算标题层级、阅读顺序、表格结构或网页正文抽取准确率。本轮生成标注队列，只记录候选页码或 DOM selector，不把解析器结果写入金标准。

脚本：`scripts/build_external_annotation_queue.py`  
结果：[`external-annotation-queue.json`](external-annotation-queue.json)  
人工查看清单：[`EXTERNAL-ANNOTATION-QUEUE.md`](EXTERNAL-ANNOTATION-QUEUE.md)

## 2. 覆盖样本

队列包含 6 份样本：`OPEN-003`、`OPEN-010`、`OPEN-011`、`WEB-001`、`WEB-002`、`WEB-004`。

PDF 候选页由以下原因产生：开头页、文本密度最高页、文本块最多页、图片最多页。HTML 候选节点包括首个 `h1`/`h2`、参考文献标题候选、首个表格、首个代码块和 `article` 候选（若存在）。

## 3. 标注字段

PDF 标注人需要补充：

- `reading_order_rank`；
- `label`：标题、段落、页眉、页脚、脚注、表格、单元格、图注、公式、参考文献等；
- `heading_level`、`paragraph_id`、页面 bbox；
- 表格行列、合并单元格和不确定性说明。

HTML 标注人需要补充：

- 标题级别和正文标题路径；
- `body/navigation/advertisement/code/table/caption/reference` 等角色；
- DOM 父子关系、唯一 selector、图片说明和引用/锚点关系；
- 动态脚本或导航污染说明。

## 4. 约束

候选页/节点不是预测标签。标注前必须查看原始页面或 HTML 快照；标注文件应另存为 `manual-annotations/external-*.json`，不得覆盖固定查询标注。`cloud_upload_allowed` 仍为 `unknown` 的材料只在本地使用。

完成最小标注后，才能运行标题 Precision/Recall/F1、阅读顺序 pairwise accuracy、表格 cell 对齐、DOM 正文区域准确率和引用定位覆盖率。
