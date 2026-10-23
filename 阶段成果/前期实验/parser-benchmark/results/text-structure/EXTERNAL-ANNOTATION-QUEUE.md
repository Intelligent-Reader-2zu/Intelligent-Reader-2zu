# 外部样本人工标注队列

此文件只列出候选页码/DOM 位置，不包含标题层级、阅读顺序或正文角色金标准。标注前必须查看原始 PDF 页面或 HTML 快照。

## OPEN-003
来源：https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-63b.pdf
SHA-256：`ccfce7510a1267933f912d023306c6e7d485f21be63d271108b61aad6139127e`

| 页码 | 文本字符 | 块数 | 图片数 | 选择原因 |
|---:|---:|---:|---:|---|
| 1 | 1346 | 11 | 1 | opening page; verify cover, title, header/footer and first reading order |
| 8 | 3662 | 36 | 9 | maximum text density; inspect paragraph boundaries and columns |
| 69 | 1885 | 43 | 0 | maximum text block count; inspect fragmentation and reading order |
| 9 | 3462 | 36 | 14 | maximum image count; inspect figures, captions and nearby text |

标注状态：`draft`

## OPEN-010
来源：https://arxiv.org/pdf/2408.09869.pdf
SHA-256：`82dd470712ce8389f19f20eb9330475e2166a281f8c7990a9f1d0763d73b4d22`

| 页码 | 文本字符 | 块数 | 图片数 | 选择原因 |
|---:|---:|---:|---:|---|
| 1 | 2194 | 12 | 1 | opening page; verify cover, title, header/footer and first reading order |
| 7 | 16545 | 171 | 5 | maximum text density; inspect paragraph boundaries and columns |
| 3 | 3124 | 21 | 15 | maximum image count; inspect figures, captions and nearby text |

标注状态：`draft`

## OPEN-011
来源：https://arxiv.org/pdf/2204.08387.pdf
SHA-256：`bd5395610755a49e6419c406e651906e688e7a0cfe155b3c43566469dfd641fe`

| 页码 | 文本字符 | 块数 | 图片数 | 选择原因 |
|---:|---:|---:|---:|---|
| 1 | 4699 | 22 | 2 | opening page; verify cover, title, header/footer and first reading order |
| 9 | 7628 | 9 | 0 | maximum text density; inspect paragraph boundaries and columns |
| 3 | 3663 | 90 | 10 | maximum text block count; inspect fragmentation and reading order |
| 2 | 5338 | 29 | 10 | maximum image count; inspect figures, captions and nearby text |

标注状态：`draft`

## WEB-001
来源：https://www.w3.org/TR/webauthn-3/
SHA-256：`157030c980d44a3ce4b1ec5bcfaa16790c7dfefac20709af6ed2b11c7120970b`

| DOM selector | 标签 | 选择原因 |
|---|---|---|
| `html:nth-of-type(1) > head:nth-of-type(1) > body:nth-of-type(1) > div:nth-of-type(1) > h1:nth-of-type(1)` | `h1` | first h1; verify document title and root heading |
| `h2[id="abstract"]` | `h2` | first h2; verify heading path and navigation contamination |
| `h4[id="enum-attestation-convey"]` | `h4` | reference section candidate; verify citation boundary |
| `figure[id="table-authData"] > table:nth-of-type(1)` | `table` | first table; verify table role, caption and cell structure |
| `nav[id="toc"] > ol:nth-of-type(1) > li:nth-of-type(1) > li:nth-of-type(1) > li:nth-of-type(1) > li:nth-of-type(1) > li:nth-of-type(1) > ol:nth-of-type(1) > li:nth-of-type(1) > a:nth-of-type(1) > span:nth-of-type(2) > span:nth-of-type(1) > code:nth-of-type(1)` | `code` | first code candidate; verify code block boundary |

标注状态：`draft`

## WEB-002
来源：https://www.rfc-editor.org/rfc/rfc9110.html
SHA-256：`d431760660ea44e130f6e919dab216df2d0b3a490567a98089267523368fe1e5`

| DOM selector | 标签 | 选择原因 |
|---|---|---|
| `h1[id="rfcnum"]` | `h1` | first h1; verify document title and root heading |
| `h2[id="abstract"]` | `h2` | first h2; verify heading path and navigation contamination |
| `h3[id="name-uri-references"]` | `h3` | reference section candidate; verify citation boundary |
| `html:nth-of-type(1) > body:nth-of-type(1) > table:nth-of-type(1)` | `table` | first table; verify table role, caption and cell structure |
| `div[id="section-3.6-4.1"] > pre:nth-of-type(1)` | `pre` | first code candidate; verify code block boundary |

标注状态：`draft`

## WEB-004
来源：https://openstax.org/books/anatomy-and-physiology-2e/pages/1-introduction
SHA-256：`b709d19cf8bf3c3c8cf4e20933d36e7be4901ce79cf937f284f000cfabe43330`

| DOM selector | 标签 | 选择原因 |
|---|---|---|
| `div[id="root"] > div:nth-of-type(3) > div:nth-of-type(1) > div:nth-of-type(1) > h1:nth-of-type(1)` | `h1` | first h1; verify document title and root heading |
| `div[id="eip-646"] > header:nth-of-type(1) > h2:nth-of-type(1)` | `h2` | first h2; verify heading path and navigation contamination |

标注状态：`draft`
