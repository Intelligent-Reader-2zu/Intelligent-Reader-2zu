# 解析器候选方案的 Java 客户端集成说明

> 适用阶段：T07 文档解析技术可行性验证
>
> 文档状态：实验集成设计，不代表最终技术选型
>
> 关联计划：[README.md](./README.md)

## 1. 目的和边界

本文说明候选解析工具如何被 Java 客户端调用，帮助后续开展 `TECH-DOC-xxx` 实验。它只回答“如何接入和比较”，不把某个工具的官方能力描述直接转化为项目结论。

当前工作区已有的 Java 链路是 `experiments/minimal-chain-java`：

```text
Java 21 + Maven
DocumentParser.parse(Path) -> CanonicalDocument
                         -> 关键词检索 -> 引用校验
```

该实验的 `pom.xml` 当前没有 PDF、DOCX、OCR 或 Markdown 解析依赖。本文因此不修改现有 Java 代码，也不要求现在就把候选库加入生产链路。

## 2. 先统一 Java 侧的集成契约

### 2.1 不改变现有基线接口

现有接口为：

```java
public interface DocumentParser {
    CanonicalDocument parse(Path file) throws IOException;
}
```

首轮实验可为每个工具创建独立适配器，但建议把增强字段放在解析实验专用结果对象中，不立即扩展 `CanonicalDocument` 和 `DocumentBlock`。原因是当前模型没有页码、bbox、字符偏移、OCR 置信度、资产引用和解析器版本字段，贸然改动会把实验字段误当成产品合同。

### 2.2 实验适配器建议

Java 侧建议抽象成以下概念，具体类名可以在实验实现时调整：

```text
ParserAdapter
  parse(ParseRequest) -> ParseRunResult

ParseRequest
  inputPath
  outputDirectory
  languageHints
  ocrEnabled
  parserOptions

ParseRunResult
  experimentId
  sourceSha256
  parserName / parserVersion
  configHash
  rawArtifactPath
  normalizedElements
  runtimeMetrics
  failure
```

`normalizedElements` 至少保留：

```text
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

Java 客户端应同时保存三层数据：

1. 原始输入文件和 `sha256`；
2. 工具原始输出（JSON、XML、Markdown、HTML、截图或服务响应）；
3. Java 侧统一映射结果和指标。

不得只保留最后一份纯文本，否则无法复核阅读顺序、坐标和引用定位。

## 3. 四种 Java 调用模式

| 模式 | 适合候选 | Java 侧做法 | 主要风险 |
|---|---|---|---|
| 进程内依赖 | Apache Tika，以及未来确认有稳定 Java API 的库 | Maven 依赖，直接调用 Java API | 类路径冲突、原始布局字段不足、版本升级影响结果 |
| 本地 Python 进程 | PyMuPDF、pdfplumber、Docling、Unstructured、python-docx | `ProcessBuilder` 启动固定 Python runner，通过 JSON 文件或 stdin/stdout 通信 | Python 环境、进程超时、编码、stderr 污染、进程泄漏 |
| 本地 HTTP sidecar | 需要模型服务或长期驻留的 Docling/Unstructured/Python 解析器 | Java `HttpClient` 调本机 REST 服务 | 服务启动顺序、端口管理、协议版本和资源占用 |
| 云端 SDK/HTTP | Azure、Google、AWS | Java 官方 SDK 或 HTTPS 客户端 | 数据上传、凭证、区域、费用、限额、服务版本和网络失败 |

实验阶段建议每个适配器都通过统一的 `ParseRunResult` 返回，不让下游检索器知道工具是进程内、sidecar 还是云端。

## 4. 七类候选方案的集成方式

### 4.1 PyMuPDF / MuPDF

**方案性质**：Python 本地库，底层使用 MuPDF；候选矩阵关注 PDF 页面、文本块、行、span、字符和坐标。

**Java 集成建议**：

- 首选固定 Python 版本和 PyMuPDF 版本，编写 `pymupdf_runner.py`；
- Java 用 `ProcessBuilder` 传入输入文件、输出目录和 JSON 配置；
- runner 使用 `page.get_text("dict")` 或 `"rawdict"` 等结构化输出，返回页号、block、line、span、bbox；
- Java 只负责进程编排、校验 JSON schema、保存原始输出和映射到实验 IR；
- 如果后续需要常驻服务，再把同一个 runner 包装为本地 HTTP 服务，不要同时改变抽取逻辑。

**不建议首轮做法**：在 Java 中直接加载 MuPDF 原生库或自行做 JNI/JNA 封装。这样会把 native 库、平台差异和解析结果变化混到解析能力实验中。

**主要风险**：自然阅读顺序需要显式配置或后处理；扫描 PDF 不等于自动 OCR；Python 环境和原生依赖必须记录。页码和 bbox 通常可在原始输出中保存，但打印页码仍需单独识别。

**实验记录**：`TECH-DOC-001-R01`、`TECH-DOC-002-R01`、`TECH-DOC-003-R01`，保留 runner 版本、Python 版本、PyMuPDF 版本和命令行参数。

### 4.2 pdfplumber / pdfminer.six

**方案性质**：Python 本地 PDF 分析库，适合访问字符、线、矩形、图片位置和表格相关对象。

**Java 集成建议**：

- 与 PyMuPDF 采用相同的 Python runner 协议，避免为每个工具设计不同的 Java 调用方式；
- runner 输出 page、char、line、rect、table 和坐标等原始对象；
- Java 侧将其映射为 `element_type=Text/TableCandidate/AssetCandidate`，不要把表格候选直接当作已恢复表格；
- 扫描 PDF 明确作为失败对照，除非实验另行接入 OCR。

**主要风险**：官方项目定位更偏机器生成的 PDF，通常不提供 OCR；表格识别依赖页面线条和配置；字符对象多而细，Java 侧需要明确合并成段落的规则，否则段落边界会被适配器自行改变。

**实验记录**：与 PyMuPDF 在同一批样本上运行，比较原始字符召回、坐标和表格候选，不只比较最终 Markdown。

### 4.3 Docling

**方案性质**：本地文档解析框架，主要通过 Python 包和模型完成布局、阅读顺序、表格、公式、图片和 OCR 等处理。

**Java 集成建议**：

- 首轮使用固定 Python 环境或按版本核验的 Docling CLI/本地服务；
- Java 通过 `ProcessBuilder` 或本地 HTTP 调用，要求返回 `DoclingDocument` 的 JSON 或等价结构；
- 把模型下载目录、CPU/GPU、OCR 语言包和配置写入 `configHash`；
- 保留 Docling 原始 JSON，再做 Java 侧 IR 映射；不要只接收导出的 Markdown，因为 Markdown 会丢失部分 bbox、资产和层级信息；
- 只有在确认服务协议稳定后，才考虑将其作为常驻 sidecar。

**主要风险**：模型资源、首次下载、GPU/CPU 差异和版本漂移可能显著影响延迟与结果；复杂中文双栏、公式和表格必须用项目样本验证。是否存在可直接依赖的稳定 Java API 不应假设，需以实验所固定版本的官方发布物为准。

**实验记录**：`TECH-DOC-002-R01`、`TECH-DOC-003-R01`、`TECH-DOC-006-R01`，额外记录模型文件版本和硬件。

### 4.4 Unstructured OSS

**方案性质**：通用文档分区框架，可本地运行，也存在 API/托管形态；输出常见元素类型如 `Title`、`NarrativeText`、`Table`、`Header` 和 `Footer`。

**Java 集成建议**：

- 本地首轮可使用 Python runner；需要长期驻留时使用固定版本的本地 API/sidecar；
- Java 请求中明确 `strategy`、OCR、页分隔和表格相关选项，并把它们写入 `configHash`；
- 解析响应中的元素 ID、页码、坐标、类别和原始文本都要保存；
- 对 `hi_res`、`fast`、`ocr_only` 等策略分开编号，不能混在同一次结果中比较；
- `.doc` 转换、LibreOffice、OCR 后端等外部组件必须登记版本和可用性。

**主要风险**：多栏文档的排序可能不稳定；DOCX 的视觉页码依赖渲染过程；本地安装可能引入 OCR、LibreOffice 或模型依赖。元素类型是框架输出，不等于项目已经验证了标题或表格准确率。

**实验记录**：`TECH-DOC-002-R01`、`TECH-DOC-003-R01`、`TECH-DOC-004-R01`、`TECH-DOC-006-R01`，按策略拆分结果文件。

### 4.5 Apache Tika

**方案性质**：Apache 官方 Java 解析框架，适合在 Java 进程内统一做 MIME 识别、文本抽取和元数据抽取。

**Java 集成建议**：

- 在实验分支中加入固定版本的 `tika-core` 和 `tika-parsers-standard-package`，不要直接修改产品依赖；
- 使用 `TikaConfig`、`AutoDetectParser`、`ParseContext`、`Metadata` 和 `ContentHandler` 读取 PDF/Office/TXT；
- 同时保存纯文本和元数据，若需要页级或坐标级信息，应验证具体 PDF parser 的 SAX/embedded 输出是否能满足要求；
- 将 Tika 结果作为“Java 进程内基线”，与 Python 方案在同一 IR 和同一指标下比较；
- 解析异常、嵌套附件和 MIME 误判要单独记录。

实验依赖示例（版本必须在运行记录中固定，以下仅为结构示意）：

```xml
<dependency>
  <groupId>org.apache.tika</groupId>
  <artifactId>tika-core</artifactId>
  <version>${tika.version}</version>
</dependency>
<dependency>
  <groupId>org.apache.tika</groupId>
  <artifactId>tika-parsers-standard-package</artifactId>
  <version>${tika.version}</version>
</dependency>
```

**主要风险**：Tika 的统一抽取接口不自动等于完整布局解析；页码、bbox、复杂表格、公式和阅读顺序需要以实际 parser 输出验证。不要因为它是 Java 原生就假定结构化能力优于 Python 方案。

**实验记录**：`TECH-DOC-001-R01`、`TECH-DOC-004-R01`、`TECH-DOC-005-R01`，另记录依赖树和 JVM 参数。

### 4.6 python-docx + CommonMark/GFM parser

**方案性质**：Python 侧的 DOCX 和 Markdown 解析组合，不是单一服务；DOCX 依赖 OOXML 访问，Markdown 依赖具体方言和扩展。

**Java 集成建议**：

- 如果实验目的是比较“该 Python 组合”，使用一个 Python runner 同时输出 DOCX 段落、样式、表格和 Markdown AST；
- 如果实验目的是比较“Java 客户端对格式的可维护性”，另设 Java-native 对照分支，例如 Apache POI + 明确版本的 CommonMark/GFM Java 解析器；这两个分支必须分开编号，不能把替代库结果写成 python-docx 结果；
- DOCX 输出至少保留段落样式、run、表格、图片关系、页眉页脚和脚注可见性；
- Markdown 输出至少保留 AST 节点类型、源文件行列位置、链接/图片目标和扩展节点；
- Java 侧不要把 DOCX 的段落序号当作视觉页码，除非实验加入固定渲染器并验证分页。

**主要风险**：旧 `.doc` 不属于 python-docx 的直接输入；脚注和最终分页支持有限；Markdown 的 GFM 表格、脚注、数学公式等扩展并非 CommonMark 核心，解析器之间可能不一致。

**实验记录**：`TECH-DOC-004-R01`、`TECH-DOC-005-R01`，明确记录方言、扩展开关和渲染器版本。

### 4.7 Azure、Google、AWS 托管式解析服务

**方案性质**：Java 客户端通过官方 SDK 或 HTTPS 调用云端文档分析/OCR API。

**Java 集成建议**：

- 为每家服务实现独立 `CloudParserAdapter`，请求、响应、错误码和重试策略不要互相复用成隐含等价；
- 优先使用官方 Java SDK；若 SDK 无法暴露完整原始 JSON，再使用 HTTPS 客户端保存原始响应；
- 统一记录区域、endpoint、模型/processor ID、API 版本、异步 operation ID、页数/大小限制、耗时和费用；
- 凭证从环境变量或本地凭证链读取，不写入实验结果和 Git；
- 默认禁止上传 `cloud_upload_allowed != yes` 的样本；云端结果与本地结果分开编号；
- 对超时、限流、部分成功和服务不可用设置本地失败记录，不自动静默重试到改变成本。

**主要风险**：网络、区域、费用、数据驻留、服务条款和模型升级都会影响可复现性；官方示例能证明调用方式，不能证明本项目样本准确率。跨厂商返回字段需要显式映射，尤其是页码、bbox、置信度、表格和层级。

**实验记录**：建议使用 `TECH-DOC-014-R01` 等独立编号，记录服务名称、SDK 版本、区域、模型版本、请求大小、费用和原始响应哈希。

## 5. Java 客户端的最小运行布局

建议先在 `experiments/parser-benchmark` 下建立实验运行器，而不是把解析依赖直接塞进现有 `minimal-chain-java`：

```text
experiments/parser-benchmark/
  README.md
  JAVA-CLIENT-INTEGRATION.md
  samples/                 # 仅放已确认授权的样本或占位说明
  runners/                 # Python runner / sidecar 启动脚本
  java-client/             # 独立 Maven 实验模块
    src/main/java/...      # ParserAdapter、进程/HTTP/云端适配器
  results/
    raw/                    # 工具原始输出
    normalized/             # Java 统一 IR
    TECH-DOC-xxx-Rxx.md     # 指标、失败和结论
```

`java-client` 的首轮 Maven 模块可以只依赖 Java 标准库和 HTTP Client；只有 Tika 对照实验再添加 Tika 依赖。Python runner 和云端 SDK 不应成为现有最小链路的隐式运行时依赖。

## 6. 进程、HTTP 和错误处理约束

### 本地进程

- 使用绝对可记录的 Python executable、工作目录和环境变量；
- 输入路径使用参数数组传递，不拼接 shell 命令；
- stdout 只输出机器可读结果，日志写 stderr 或单独文件；
- 设置超时、最大输出大小和退出码检查；
- 进程失败时保存命令摘要、stderr、版本和输入哈希，不自动把空文本当作成功。

### 本地 HTTP

- 固定服务版本、端口、健康检查和启动脚本；
- 请求中携带 `experiment_id`、`source_sha256` 和 `config_hash`；
- 设置连接、读取和总超时，区分 4xx 配置错误、5xx 服务错误和客户端取消；
- 保留响应 JSON、HTTP 状态、服务日志位置和资源使用量。

### 云端

- 凭证、区域和 endpoint 通过外部配置注入；
- 重试只针对明确的瞬时错误，并记录每次重试；
- 达到费用、页数或大小上限时返回可见失败，不自动切换到未经授权的服务；
- 保存服务返回的版本字段或请求 ID，确保后续能追溯。

## 7. 最小通信协议示例

下面的协议只是实验约定，不是产品 API。所有本地 Python 工具先采用同一输入输出格式，避免 Java 客户端被某个工具的参数格式锁定。

### 7.1 本地 Python runner

Java 侧可以启动类似下面的命令（参数使用数组传递，不拼接 shell 字符串）：

```text
python runners/run_parser.py --request request.json --response response.json
```

`request.json`：

```json
{
  "experiment_id": "TECH-DOC-001-R01",
  "input_path": "samples/S1.pdf",
  "output_dir": "results/raw/TECH-DOC-001-R01",
  "parser": "pymupdf",
  "parser_version": "固定版本",
  "options": {
    "ocr_enabled": false,
    "language_hints": ["zh", "en"]
  }
}
```

`response.json` 至少包含：

```json
{
  "status": "succeeded",
  "source_sha256": "...",
  "parser": "pymupdf",
  "parser_version": "...",
  "raw_artifact": "results/raw/TECH-DOC-001-R01/output.json",
  "elements": [],
  "metrics": {
    "elapsed_ms": 0
  },
  "failure": null
}
```

Java 侧必须检查进程退出码、`status`、输入哈希和响应文件是否存在；空的 `elements` 不能在没有 `failure` 记录时被视为解析成功。

### 7.2 本地 HTTP sidecar

建议沿用相同 JSON 结构：

```text
POST http://127.0.0.1:<fixed-port>/parse
Content-Type: application/json
```

响应继续使用 `response.json` 的字段。Java 侧记录 HTTP 状态、请求耗时、服务版本和响应原文；连接失败、超时、4xx、5xx 要区分记录。sidecar 只改变传输方式，不改变解析器原始输出和统一 IR 映射。

### 7.3 云端适配器

云端适配器也应先转换为相同的 `ParseRunResult`，但必须额外保存：

```text
provider
region
endpoint
model_or_processor_id
api_version
request_id / operation_id
billable_pages_or_units
```

这样可以把“Java 能否调用服务”和“服务对项目样本是否准确”分成两个可独立复核的问题。

## 8. 推荐的实验顺序（不是最终选型）

1. 先复验现有 Markdown/TXT Java 基线 `TECH-ARCH-001-R01`。
2. 用 Apache Tika 建立 Java 进程内对照，确认统一适配器和结果记录格式。
3. 用 PyMuPDF、pdfplumber 建立最小 PDF 本地进程对照，先验证页码、bbox 和阅读顺序记录能力。
4. 加入 Docling、Unstructured，比较布局/OCR/表格结果，并单独记录模型和外部依赖。
5. 用 python-docx + Markdown parser 验证 DOCX/Markdown 结构，再决定是否增加 Java-native 对照。
6. 样本授权和合规条件满足后，最后接入 Azure、Google、AWS 中的候选服务。

这样安排的目的，是先验证 Java 侧适配协议和证据保存是否稳定，再比较解析质量；它不表示 Tika 或任何本地方案已经被选定。

## 9. 证据来源和事实边界

以下为集成方式的主要官方资料入口；它们用于确认调用形态、输出接口和服务约束，不等于本项目样本上的质量结论。

| 候选 | 资料类型 | 入口 | 用途 |
|---|---|---|---|
| PyMuPDF | 官方文档 | [PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/) | Python 安装、TextPage/DICT/RAWDICT 和页面对象 |
| pdfplumber | 开源项目文档 | [pdfplumber README](https://github.com/jsvine/pdfplumber) | Python API、字符/页面/表格对象和限制说明 |
| Docling | 官方文档/开源项目 | [Docling documentation](https://docling-project.github.io/docling/) | 本地运行、文档模型和导出接口；Java 接口需按版本核验 |
| Unstructured | 官方文档 | [Partitioning](https://docs.unstructured.io/open-source/core-functionality/partitioning) | 本地分区、策略和元素输出；服务形态需固定版本 |
| Apache Tika | 官方文档 | [Apache Tika](https://tika.apache.org/) | Java 依赖、Parser、Metadata 和内容抽取接口 |
| python-docx | 官方文档 | [python-docx documentation](https://python-docx.readthedocs.io/en/latest/) | DOCX 段落、样式、表格和 run API |
| CommonMark | 标准规范 | [CommonMark specification](https://spec.commonmark.org/) | 核心 Markdown 语法；GFM/脚注/数学公式需另行核对 |
| Azure | 官方 Java SDK 文档 | [Azure Document Intelligence client library](https://learn.microsoft.com/en-us/java/api/overview/azure/ai-documentintelligence-readme?view=azure-java-stable) | Java SDK、认证和分析请求 |
| Google | 官方 Java API 文档 | [Google Cloud Document AI Java client](https://cloud.google.com/java/docs/reference/google-cloud-document-ai/latest/overview) | Java 客户端、处理器调用和响应对象 |
| AWS | 官方 Java SDK 文档 | [AWS SDK for Java Textract examples](https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/java_textract_code_examples.html) | Textract Java 调用示例和错误处理 |

需要进一步核验的事实：具体版本是否提供稳定 CLI/REST 协议、Docling/Unstructured 的服务启动方式、云端 SDK 的字段覆盖、各工具对中文和复杂布局的真实准确率。这些内容应在实验记录中标记为 `R（待验证/风险）`，不能仅依据文档页面下结论。

## 10. 可记录的验证项

- `TECH-DOC-016`：Java `ParserAdapter` 是否能统一接收进程内、Python 进程、HTTP 和云端结果。
- `TECH-DOC-017`：PyMuPDF 与 pdfplumber 原始输出能否保留页码、bbox、字符/块层级并可回溯。
- `TECH-DOC-018`：Docling/Unstructured 本地 runner 或 sidecar 的版本、模型和资源是否可复现。
- `TECH-DOC-019`：Apache Tika Java 进程内解析与 Python 方案在同一 IR 下的字段覆盖差异。
- `TECH-DOC-020`：python-docx/CommonMark 组合与 Java-native 对照的结构字段和分页差异。
- `TECH-DOC-021`：云端 Java SDK/HTTP 的原始响应、模型版本、限额、费用和失败重试是否可记录。
- `TECH-DOC-022`：解析器进程/服务失败时，Java 客户端是否能阻止空结果进入检索和问答。
