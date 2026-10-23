# TECH-RET-010-R01 真实解析 IR 检索与证据回溯

样本：SELF-001, SELF-002, SELF-003, SELF-005, SELF-008；载入文档：5；块数：80；问题数：12。

固定片段 Hit@3：**0.833**；返回证据元数据完整率：**0.606**。

该实验直接读取已有 PyMuPDF/Markdown 等解析 IR，验证检索结果能否带回源哈希、物理页码、bbox、字符偏移和原文；它不代表向量检索质量，也不替代人工阅读顺序/标题结构验收。

| 样本 | 查询片段 | Gold | Top-3 | 命中 | 页码/bbox/字符偏移可回溯 |
|---|---|---|---|---|---|
| SELF-001 | 物理页码 | self-001-0391dd982a1c-e0006 | self-001-0391dd982a1c-e0006,self-001-0391dd982a1c-e0004,self-001-0391dd982a1c-e0008 | YES | YES |
| SELF-001 | 标题路径 | self-001-0391dd982a1c-e0006 | self-001-0391dd982a1c-e0006,self-001-0391dd982a1c-e0004,self-001-0391dd982a1c-e0009 | YES | YES |
| SELF-001 | 脚注占位 | self-001-0391dd982a1c-e0010 | self-001-0391dd982a1c-e0010,self-001-0391dd982a1c-e0004,self-001-0391dd982a1c-e0006 | YES | YES |
| SELF-002 | 跨栏标题和参考文献 | self-002-614c8a0cd2fe-e0003 | self-002-614c8a0cd2fe-e0003,self-002-614c8a0cd2fe-e0006,self-002-614c8a0cd2fe-e0019 | YES | YES |
| SELF-002 | 第二页用于检查页码 | self-002-614c8a0cd2fe-e0024 | self-002-614c8a0cd2fe-e0024,self-002-614c8a0cd2fe-e0006,self-002-614c8a0cd2fe-e0013 | YES | YES |
| SELF-003 | Recall@k | self-003-e0776c95d8ff-e0004,self-003-e0776c95d8ff-e0008 | self-003-e0776c95d8ff-e0004,self-003-e0776c95d8ff-e0008 | YES | YES |
| SELF-003 | 合并单元格需保留 | self-003-e0776c95d8ff-e0009 | self-003-e0776c95d8ff-e0009,self-003-e0776c95d8ff-e0004,self-003-e0776c95d8ff-e0006 | YES | YES |
| SELF-005 | Heading 1/2/3 | (none) | self-005-77ddbb18413f-e0007 | NO | NO |
| SELF-005 | 稳定 block identifiers | (none) | self-005-77ddbb18413f-e0007,self-005-77ddbb18413f-e0005,self-005-77ddbb18413f-e0015 | NO | NO |
| SELF-008 | 稳定的 `block_id` | self-008-47b74431f9c8-e0005 | self-008-47b74431f9c8-e0005,self-008-47b74431f9c8-e0002,self-008-47b74431f9c8-e0004 | YES | NO |
| SELF-008 | 引用定位率 | self-008-47b74431f9c8-e0007 | self-008-47b74431f9c8-e0007,self-008-47b74431f9c8-e0015,self-008-47b74431f9c8-e0016 | YES | NO |
| SELF-008 | 这是一个脚注 | self-008-47b74431f9c8-e0017 | self-008-47b74431f9c8-e0017,self-008-47b74431f9c8-e0003,self-008-47b74431f9c8-e0016 | YES | NO |
