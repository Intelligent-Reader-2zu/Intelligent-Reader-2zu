# 候选服务的访问前置条件

> 本文只说明实验前置条件，不代表项目已决定使用云端服务。

## 本地工具

以下候选通常不需要登录或付费账号，可在本地环境安装和运行；模型、OCR 语言包或系统组件可能需要另行下载和固定版本：

| 候选 | 登录/付费 | 当前状态 |
|---|---|---|
| PyMuPDF | 不需要云端账号；本地 Python 包 | 已安装，可运行 `TECH-DOC-001-R01-local-baseline` |
| pdfplumber | 不需要云端账号；本地 Python 包 | 已安装 `0.11.10`，已完成 `SELF-001` 至 `SELF-004` 冒烟测试 |
| Docling | 本地运行通常不需要云端账号；模型资源可能需要下载 | 已安装 `2.130.0`，已完成 `SELF-001` 至 `SELF-004` 冒烟测试；首次运行需下载模型并使用 ASCII 临时/缓存路径 |
| Unstructured OSS | 本地 OSS 不需要托管账号；部分 OCR/转换器有额外依赖 | 已安装 `0.27.8`（含 `unstructured-inference 1.6.13`）；`fast` 已完成，`hi_res`/`ocr_only` 的中文 OCR 受 Windows hOCR 编码错误阻塞 |
| Apache Tika | 不需要账号；本地 Java/Maven 依赖 | 尚未加入独立实验模块 |
| python-docx | 不需要账号；本地 Python 包 | 已安装 |
| CommonMark/GFM 解析器 | 不需要账号；本地库 | `markdown-it-py` 已安装，GFM 扩展尚未单独配置 |

## 需要账号、凭证或可能产生费用的服务

以下服务若要执行真实 API 实验，通常需要提前准备云厂商账号、项目/订阅、区域和凭证；是否必须开通付费取决于当前账户、免费额度和服务政策，不能由本地代码保证：

| 服务 | 需要提前准备 | 费用/合规注意 |
|---|---|---|
| Azure AI Document Intelligence Layout | Azure 订阅、资源、区域、endpoint、API key 或 Entra 凭证 | 通常按页或交易计费；免费层/试用额度和区域可用性需在 Azure 门户确认；样本上传前需确认数据处理和驻留条件 |
| Google Cloud Document AI Layout Parser | Google Cloud 项目、启用 API、结算账号、processor/region 和服务账号凭证 | 通常按页计费；无结算账号时可能无法创建或调用 processor；需确认区域、保留和日志策略 |
| AWS Textract | AWS 账号、区域、IAM 用户/角色和访问密钥或默认凭证链 | 按页/功能计费；新账号可能有试用额度但不能假定；需设置预算、限额和数据区域 |
| Unstructured API/托管形态 | Unstructured 账户、API key、endpoint | 与本地 OSS 分开；套餐、限额和数据处理政策需单独核对 |

本次本地测试还安装了 Tesseract 5.5.3 及 `eng`、`chi_sim` 训练数据，供 Unstructured `hi_res`/`ocr_only` 使用；这些是本地系统依赖，不需要账号或付费，但需要单独管理版本和模型文件。

## 对当前实验的决定

本轮不要求你提前登录或付费。当前授权清单中的 `cloud_upload_allowed` 仍为 `unknown` 或 `no`，因此不应上传到 Azure、Google、AWS 或 Unstructured 托管服务。

如果后续要执行云端对比，先由项目负责人确认：

1. 哪些样本允许上传，以及允许的区域；
2. 是否接受按页计费和最低消费；
3. 是否需要建立独立测试订阅/项目和预算告警；
4. 是否允许保存服务原始响应、请求 ID 和日志；
5. 服务版本、限额和数据留存政策如何登记。

准备好这些条件后，再为 Azure、Google 和 AWS 分别创建 `TECH-DOC-014-Rxx` 结果，不把云端调用作为本地实验的隐式依赖。
