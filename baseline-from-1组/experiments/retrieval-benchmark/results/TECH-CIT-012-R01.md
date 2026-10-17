# TECH-CIT-012-R01 版本与索引漂移

| 用例 | 变化 | 期望 | 实际 | 结果 |
|---|---|---|---|---|
| `V01` | parser_config_changed_same_source | `stale` | `stale` | PASS |
| `V02` | source_hash_changed | `stale` | `stale` | PASS |
| `V03` | same_source_same_config | `valid` | `valid` | PASS |

结论：同源文件更换解析配置也会使 offset/block 语义发生变化；旧引用必须标 stale，不得静默重定向到新索引。
