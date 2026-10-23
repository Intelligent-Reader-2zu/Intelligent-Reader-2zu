# TECH-CIT-009-R01 引用跳转与核验路由契约

生成路由：**5**；核心路由字段完整率：**1.000**。

| citation | 模式 | 文档版本 | 页码 | 结果 |
|---|---|---|---:|---|
| `self-001-0391dd982a1c::self-001-0391dd982a1c-e0001` | `page_bbox` | `da8fe3be20b08bc1` | 1 | PASS |
| `self-001-0391dd982a1c::self-001-0391dd982a1c-e0002` | `page_bbox` | `da8fe3be20b08bc1` | 1 | PASS |
| `self-001-0391dd982a1c::self-001-0391dd982a1c-e0003` | `page_bbox` | `da8fe3be20b08bc1` | 1 | PASS |
| `self-005-77ddbb18413f::self-005-77ddbb18413f-e0001` | `section_paragraph` | `e3f9db6145cb359b` | - | PASS |
| `self-005-77ddbb18413f::self-005-77ddbb18413f-e0002` | `section_paragraph` | `e3f9db6145cb359b` | - | PASS |

结论：PDF/扫描块使用 page_bbox 路由，DOCX/Markdown 使用 section_paragraph 路由；页面或高亮不可用时，路由状态必须显式降级。
