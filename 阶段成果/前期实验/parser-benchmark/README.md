# Parser Benchmark Plan

这是 T07 文档解析环节的独立最小实验计划，不是阅读器产品实现，也不代表最终解析器选型。

Java 客户端的调用模式、适配器契约和七类候选工具的集成说明见：[JAVA-CLIENT-INTEGRATION.md](./JAVA-CLIENT-INTEGRATION.md)。

本地基线运行器、结果摘要和服务账号前置条件见：[LOCAL-BASELINE-RESULT.md](./LOCAL-BASELINE-RESULT.md)、[SERVICE-ACCESS.md](./SERVICE-ACCESS.md)；脚本为 `scripts/run_local_baseline.py`。

本轮非 OCR 文本结构实验结果见：[TECH-DOC-007-R01.md](./results/text-structure/TECH-DOC-007-R01.md)。结果目录同时保留 PyMuPDF/pdfplumber、Docling（`do_ocr=false`）和 Apache Tika 的原始 JSON；扫描 PDF `SELF-004` 仅记录无文本层，不纳入 OCR 或结构评分。

下一轮 `TECH-DOC-007-R02` 已增加 PyMuPDF `DICT/RAWDICT` 原始结构、自动证据检查和人工标注流程：[TECH-DOC-007-R02.md](./results/text-structure/TECH-DOC-007-R02.md)。阅读顺序、段落边界、标题层级和表格网格已由用户通过自然语言逐项确认，不能由固定关键词命中率替代。

三份文本型 PDF 的人工确认和结构评分已经完成，结果见：[TECH-DOC-007-R02-MANUAL-SCORE.md](./results/text-structure/TECH-DOC-007-R02-MANUAL-SCORE.md)。评分脚本会校验标注与解析结果的源文件哈希，字段缺失记为 `not_available`。

pdfplumber、Docling、Unstructured 的隔离环境版本、PDF 冒烟测试记录和复跑命令见：[CANDIDATE-PDF-RESULT.md](./CANDIDATE-PDF-RESULT.md)；直接依赖版本见 `requirements-candidates.txt`。

OCR 专项的候选类别、扫描 PDF/图片文档最小实验、固定问题集、指标、降级策略和一期范围建议见：[T07-OCR技术调研.md](../../工作区/需求调研/A-work/T07-OCR技术调研.md)。`SELF-004` 的独立 Tesseract 基线原始结果见 `results/ocr-baseline/summary.json`；该结果只有运行状态和置信度观测，没有逐字金标准，因此不构成 OCR 质量验收。

当前 OCR 最小实验结果：`TECH-OCR-001-R01` 的配置矩阵见 `results/ocr-tesseract-matrix/TECH-OCR-001-R01.md`，受控低质量退化实验 `TECH-OCR-002-R01` 见 `results/ocr-degradation-matrix/TECH-OCR-002-R01.md`；逐字参考文本为 `samples/self-authored/annotations/SELF-004-ocr-ground-truth.json`。这些结果仅适用于当前 `SELF-004` 哈希，不能替代真实扫描件评测。

RapidOCR 3.9.2 + ONNX Runtime 已完成同样本对照：`TECH-OCR-015-R01` 见 `results/ocr-rapidocr/TECH-OCR-015-R01.md`，脚本为 `scripts/run_ocr_rapidocr.py`。该结果证明隔离环境中的本地 ONNX 链路可运行并返回行级 polygon bbox；中文替代字符和英文/数字错误仍需按字符级金标准解释，不能只看置信度或关键词召回。

固定关键字符串的页面召回检查见 `results/ocr-downstream/TECH-OCR-009-R01.md`。它不验证语义检索、回答正确率或引用框覆盖率。

## 目标和边界

验证文本型 PDF、扫描型 PDF、DOCX、Markdown 和 TXT 在正文、结构、版式、语言和证据定位方面的可行性，并为一期支持格式、质量指标和降级方案提供可追溯证据。

本实验首轮只做本地、离线、授权样本的解析对比。暂不上传项目资料，暂不引入产品依赖，暂不同时替换检索器、模型或问答链路。

已有 `experiments/minimal-chain-java` 的 `TECH-ARCH-001-R01` 仅作为 Markdown/TXT 和 block ID 引用校验的基线。解析器实验使用 `TECH-DOC-xxx` 编号，不能覆盖或改写架构实验结论。

## 样本登记

首轮使用 3-6 份短样本，每份建议 2-10 页或等量内容。样本必须能证明使用许可；公开下载不等于允许上传云端。

| 字段 | 要求 |
|---|---|
| `sample_id` | `S1`、`S2` 等稳定编号 |
| `source` | 来源标题、作者/机构、链接或存放位置 |
| `license_or_authorization` | 许可证、授权人、授权范围和日期 |
| `format` | PDF text / PDF scan / DOCX / MD / TXT |
| `pages` | 页数；对 MD/TXT 记录行数或字符数 |
| `languages` | 中文、英文或混排 |
| `layout_features` | 单栏、双栏、表格、公式、图片、脚注等 |
| `expected_risks` | 预先登记的风险 |
| `cloud_upload_allowed` | `yes` / `no` / `unknown`；`unknown` 不上传 |
| `sha256` | 原始文件哈希 |

## 自制样本生成器

预期的 40 份候选清单见 [`EXPECTED-SAMPLES.md`](./EXPECTED-SAMPLES.md)。其中项目组自制样本由 [`scripts/generate_self_authored_samples.py`](./scripts/generate_self_authored_samples.py) 生成，默认输出到 `samples/self-authored/`：

```powershell
python scripts/generate_self_authored_samples.py --strict
```

生成器会产出 Markdown、UTF-8/GB18030 TXT、HTML 快照、DOCX、文本型 PDF 和图像型扫描 PDF，并写入 `self-authored-manifest.json`。manifest 包含文件哈希、页数/行数、版面特征、预期风险和人工参考标注路径。自制样本默认 `cloud_upload_allowed=no`，即使内容由项目组生成，也应先在本地完成解析对比。

公开候选样本由 [`scripts/download_public_candidates.ps1`](./scripts/download_public_candidates.ps1) 登记和下载，结果写入 [`samples/external-candidates/external-candidate-manifest.json`](./samples/external-candidates/external-candidate-manifest.json)。脚本会先下载到临时文件，再按大小上限检查，并记录 SHA-256、来源 URL、失败原因和 `cloud_upload_allowed=unknown`。清单中的 `skipped` 项不能视为已获得样本；需要重新核对官方页面或改用合适的公开许可来源。

原清单中无法稳定取得的 12 个外部名额使用 [`scripts/download_external_replacements.ps1`](./scripts/download_external_replacements.ps1) 处理，替代文件和对应关系见 [`samples/external-replacements/external-replacement-manifest.json`](./samples/external-replacements/external-replacement-manifest.json)。这些文件是开放文档或政府公开报告替代，不声称仍具备原公共领域扫描件的特征；许可证和云端上传权限仍需逐项复核。

用户提供的授权材料登记在 [`samples/open-authored/manifest.json`](./samples/open-authored/manifest.json)。其中 `AUTH-001` 至 `AUTH-004` 指向 `open-authored/` 中的实际文件；`AUTH-005`、`AUTH-006` 使用 `open-authored-substitutes/` 下的开放来源替代，并明确标记为 substitute，不计入已确认授权真实材料，除非后续确认其使用范围。

PDF 生成需要本地的 `reportlab`、`Pillow` 和可用 Unicode 字体；缺少这些依赖时，默认会跳过对应 PDF 并给出警告，`--strict` 会让运行失败，避免把不完整的样本集当成完整结果。

建议的最小样本组合：

1. 文本型单栏 PDF，含标题、页眉页脚、脚注和中英文混排；
2. 文本型双栏 PDF，含跨栏标题、表格、图片或参考文献；
3. 扫描型中文 PDF，含英文缩写、倾斜或低清页面；
4. DOCX，含 Heading 1/2/3、表格、分页符、页眉页脚和脚注；
5. Markdown，含 GFM 表格、代码块、脚注、数学公式和图片链接；
6. TXT，覆盖 UTF-8/GB18030、CRLF/LF、空行和中英文混排。

## 候选工具矩阵

首轮固定版本后比较，不把官方能力描述直接当成项目结论。

| 类别 | 候选 | 首轮关注点 | 部署 |
|---|---|---|---|
| PDF 独立库 | PyMuPDF | blocks/words/DICT、页码、bbox、阅读顺序 | 本地 |
| PDF 独立库 | pdfplumber | 字符/线/矩形、表格和坐标；扫描 PDF 明确作为失败对照 | 本地 |
| 通用框架 | Docling | 布局、阅读顺序、表格、公式、图片、OCR 和统一文档树 | 本地，可 CPU/GPU |
| 通用框架 | Unstructured | 元素类型、页分隔、OCR、表格和多栏排序 | 本地；另有 API/托管形态 |
| 通用框架 | Apache Tika | MIME 识别、PDF/Office/TXT 统一抽取接口 | 本地 Java |
| Office/文本库 | python-docx + CommonMark/GFM parser | DOCX 样式与表格；Markdown AST、方言和扩展 | 本地 |
| 托管服务（可选） | Azure Layout、Google Layout Parser、AWS Textract | 云端准确率、限额、费用、区域和版本漂移 | 云端，需授权后 |

## 实验步骤

### Phase 0：人工参考和复现基线

- 为每份样本标注正文、标题级别、段落、物理页码、打印页码、页眉、页脚、脚注、表格、图片和公式区域。
- 复验 `TECH-ARCH-001-R01`，记录输入哈希、运行环境、block 数量、标题路径、行号和引用校验结果。

### Phase 1：本地解析对比

- 固定工具版本、模型版本、配置、操作系统和运行命令。
- 每个工具单独运行，保留原始 JSON/HTML/Markdown、日志、异常和页面截图；不能只保存一份扁平纯文本。
- 同一工具先比较默认配置，再针对双栏、OCR、表格等风险记录明确的配置变化。

### Phase 2：统一 IR 映射

不要求立即修改生产模型。先建立实验适配层，至少记录：

```text
doc_id
source_hash
source_format
parser_name
parser_version
config_hash
element_id
element_type
text
physical_page
printed_page_label
bbox
line_start / line_end
char_start / char_end
heading_path
parent_element_id
confidence
asset_ref
```

对照现有 `DocumentBlock`，登记哪些字段可以直接映射、哪些字段缺失、哪些字段只能作为风险或降级信息保存。

### Phase 3：下游证据定位检查

使用固定查询对每个解析结果做最小关键词检索，只检查解析是否能支持证据回溯：命中的文本块、标题路径、物理页码和 bbox 是否仍能定位到原始页面。不要据此推导向量检索或问答模型质量。

### Phase 4：云端候选（可选）

仅当样本授权、数据驻留、区域、费用和服务条款均已确认时执行。记录上传区域、模型版本、请求限制、处理时间、费用和原始响应；与本地结果分开编号，不能混合平均。

## 指标记录

### 内容和结构

- 正文字符召回率；扫描 PDF 的 OCR CER、英文 WER；
- 阅读顺序正确率；段落边界 Precision/Recall/F1；
- 标题识别 Precision/Recall/F1 和层级准确率；
- 物理页码、打印页码和 bbox 映射准确率；
- 页眉页脚误归入正文比例、脚注保留率；
- 表格单元格文本准确率、行列/合并单元格结构准确率；
- 图片和公式区域检测召回率；中英文混排及特殊符号错误率。

### 工程和可复现性

- 单页/整文档 p50、p95 延迟，CPU、内存和 GPU 使用量；
- 失败率、超时率、异常类型、批处理吞吐和输出大小；
- 固定版本升级前后的结果漂移；
- 云端服务的费用、页数/文件大小限额、区域和数据留存政策。

### 下游可用性

- 固定查询命中正确页码的比例；
- 引用 bbox 是否覆盖参考答案证据；
- 标题路径是否随检索块保留；
- OCR 低置信度内容是否可被标记；
- 表格/公式是否被错误当作普通段落。

## 实验编号和结果模板

| 编号 | 样本 | 目的 |
|---|---|---|
| `TECH-DOC-001-R01` | S1 文本型单栏 PDF | 正文、页码、阅读顺序、段落 |
| `TECH-DOC-002-R01` | S2 双栏 PDF | 栏顺序、跨栏标题、脚注、参考文献 |
| `TECH-DOC-003-R01` | S3 扫描型中文 PDF | OCR、中英文混排、低置信度 |
| `TECH-DOC-004-R01` | S4 DOCX | 样式、表格、页眉页脚、脚注、分页 |
| `TECH-DOC-005-R01` | S5/S6 Markdown/TXT | 方言、编码、换行、段落归一化 |
| `TECH-DOC-006-R01` | 含表格/图片/公式样本 | 资产、结构和降级展示 |

每次运行至少记录：

```text
experiment_id
date
sample_id
source_sha256
tool / version
config_hash
runtime
raw_output_path
metrics
failure_cases
interpretation (I)
technical_or_scope_conclusion (C)
open_risks (R)
evidence_links
```

结果文件建议放在 `experiments/parser-benchmark/results/`，并按实验编号保存；没有完成运行前不要填写通过/不通过结论。

当前可复现的本地基线命令：

```powershell
python -B experiments/parser-benchmark/scripts/run_local_baseline.py --kind all
```

该命令只调用已安装的本地工具，不接入云端服务；缺失的 `pdfplumber`、Docling、Unstructured 和 OCR 适配器会记录为未安装或未运行，不自动下载或替换。

本轮还记录了 PaddleOCR 候选：`PaddleOCR 2.10.0 + PaddlePaddle 3.3.1` 的模型下载/初始化成功，但 Windows/Python 3.13 CPU 推理在 OneDNN `fused_conv2d` 处失败，见 `results/ocr-paddleocr/TECH-OCR-016-R01.md`。该结果属于环境兼容性阻塞，不能作为识别质量结论；模型缓存已固定到 ASCII 项目路径，避免中文用户目录路径问题。

独立 Python 3.11.16 环境中的成功复测见 `results/ocr-paddleocr/TECH-OCR-016-R02.md`：PaddlePaddle 2.6.2 + PaddleOCR 2.10.0 在 144/300 DPI 两页均成功，保存行 polygon、置信度、CER/WER 和 5 次热运行时延。复现顶层依赖为 `requirements-paddle311.txt`。

PP-StructureV2 的布局/表格 smoke test 见 `results/ocr-ppstructure/TECH-OCR-018-R01.md`。layout-only 可返回双栏页面的标题、正文、参考文献、页脚和表格区域，但扫描页整页被归类为 figure；完整表格子模型与当前 Paddle 2.6.2 初始化不兼容，未形成单元格或 HTML 质量结论。

EasyOCR 的独立环境验证见 `results/ocr-easyocr/TECH-OCR-019-R01.md`。Python 3.11 + PyTorch 2.14 CPU 可正常运行，但 EasyOCR 模型下载端点的证书链在默认 CA 和 Windows 系统证书下均不受信任，因此未进入推理，也没有质量结论。未关闭 TLS 校验；后续应走受信任制品库的离线模型流程。

PP-StructureV3 的完整布局/表格实验见 `results/ocr-ppstructure-v3/TECH-OCR-020-R01-R03.md`。关闭 MKL-DNN 后，双栏表格页能输出布局、3x3 网格、9 个单元格框和 HTML，但只有 5/9 个单元格内容位于正确 HTML 位置，CPU 页面时延约 823 秒；原尺寸扫描页可复现原生进程退出，1000 像素宽诊断变体成功但仍需约 119 秒。该候选目前只适合异步增强实验，不进入一期同步主路径。复现依赖为 `requirements-paddle3.txt`。

RapidOCR 的五组退化图复测见 `results/ocr-rapidocr-degradation/TECH-OCR-021-R01.md`，复现依赖为 `requirements-rapidocr.txt`。五组均返回文本和 bbox，但全字符 CER 最高 8.73%、英文/数字 WER 最高 16.67%，说明关键字全命中仍不能直接放行精确问答。

一期统一门槛与回退建议见 `results/ocr-phase1-gate/TECH-OCR-022-R01.md`。当前两页清晰自制样本上只有 RapidOCR 144 DPI 全项通过；Tesseract 300 DPI 作为第二本地引擎重试但自身仍有复合编号查询漏检。该门槛必须在至少 5 份真实授权扫描 PDF 上重新标定后，才能成为产品验收标准。

公开样本来源、固定提交、许可证边界和排除记录见 `results/ocr-public-samples/TECH-OCR-023-R01.md`；完整清单为 `samples/public-ocr/manifest.json`。浏览器访问公开站点受当前网络阻断后，样本通过 GitHub 官方 `git/blob` API 按 SHA 获取，未关闭 TLS 校验，且全部标为 `cloud_upload_allowed=no`。

公开图片一期门槛复测见 `results/ocr-public-samples/TECH-OCR-024-R01.md`，脚本为 `scripts/run_ocr_public_samples.py`。RapidOCR/Tesseract 在 8 张图上均完成运行，但固定问题仅通过 4/11 和 3/11；180 度页均失败，表格 token 即使在 RapidOCR 平均置信度 98% 以上也没有保持同一行关系。该结果支持原有“清晰正向单栏最佳努力”范围，不支持扩大到倒置页、表格、公式或印章结构化问答。

OCRmyPDF `17.12.1` 的可搜索 PDF 验证见 `results/ocrmypdf/TECH-OCR-017-R01.md`。`sandwich` 渲染路径保留了两页页面尺寸和可视原图，英文/数字可检索；当前 Windows/Tesseract 中文文本层经 `pypdf` 提取为乱码，因此不能直接作为中文检索或引用来源。默认 hOCR 路径仍复现 XML 编码错误。

## 失败场景和降级策略

| 失败 | 降级 |
|---|---|
| PDF 阅读顺序错误 | 页面级文本或按列裁剪提取，并标记布局不保证 |
| OCR 置信度低 | OCR 文本 + 原页截图 + 低置信度标记 |
| 中文混排字符错误 | 同时保留原图、OCR 文本和字符置信度；禁止强断言 |
| 表格结构失败 | 表格截图和线性化文本；不承诺单元格问答 |
| 公式无法识别 | 保留公式区域截图/bbox；不把错误 OCR 当作公式文本 |
| 页眉页脚污染正文 | 保留元素类型，检索时降权而非静默删除 |
| DOCX 无稳定视觉页码 | 使用标题路径、段落索引和字符偏移 |
| `.doc` 或转换失败 | 一期仅承诺 `.docx`，旧格式进入转换/人工队列 |
| 云端超限或不可用 | 本地基础解析兜底，限制大小/页数并异步处理 |

## 首轮完成判定

首轮实验完成不等于选型完成。只有在每种样本至少有一份原始输出、指标记录、失败案例和证据链接后，才可形成阶段性范围建议。任何“支持/不支持”表述都必须注明样本、工具版本和实验编号。

在实验结果产生前，只能记录以下待决策事项：一期是否支持扫描 PDF、是否允许云端、是否承诺复杂表格/公式、引用定位需要达到页级还是 bbox 级，以及 DOCX 是否需要稳定视觉页码。
