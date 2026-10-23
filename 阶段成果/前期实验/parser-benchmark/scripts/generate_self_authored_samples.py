#!/usr/bin/env python3
"""Generate deterministic, self-authored documents for parser experiments.

The generated corpus is intentionally small and controlled. It is a source of
known-answer samples, not a replacement for the licensed 40-document corpus.
Optional PDF generation requires reportlab and Pillow. DOCX generation uses
minimal OOXML written with the standard library so the structure is explicit.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import sys
import textwrap
import zipfile
from pathlib import Path
from typing import Any


SCRIPT_VERSION = "1.0"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "samples" / "self-authored"


class OptionalDependencyError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def save_text(path: Path, text: str, encoding: str = "utf-8", newline: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if newline is not None:
        text = text.replace("\n", newline)
    path.write_bytes(text.encode(encoding))


def xml_escape(value: str) -> str:
    return html.escape(value, quote=False)


def run_xml(text: str, *, bold: bool = False, italic: bool = False) -> str:
    properties = []
    if bold:
        properties.append("<w:b/>")
    if italic:
        properties.append("<w:i/>")
    run_properties = f"<w:rPr>{''.join(properties)}</w:rPr>" if properties else ""
    return f"<w:r>{run_properties}<w:t xml:space=\"preserve\">{xml_escape(text)}</w:t></w:r>"


def paragraph_xml(text: str = "", style: str | None = None, *, bold: bool = False) -> str:
    p_properties = f"<w:pPr><w:pStyle w:val=\"{style}\"/></w:pPr>" if style else ""
    return f"<w:p>{p_properties}{run_xml(text, bold=bold)}</w:p>"


def table_xml(rows: list[list[str]]) -> str:
    body = []
    for row_index, row in enumerate(rows):
        cells = []
        for cell in row:
            cells.append(
                "<w:tc><w:tcPr><w:tcW w:w=\"2400\" w:type=\"dxa\"/></w:tcPr>"
                + paragraph_xml(cell, bold=row_index == 0)
                + "</w:tc>"
            )
        body.append("<w:tr>" + "".join(cells) + "</w:tr>")
    return "<w:tbl><w:tblPr><w:tblStyle w:val=\"TableGrid\"/></w:tblPr>" + "".join(body) + "</w:tbl>"


def make_docx(path: Path, variant: str) -> None:
    if variant == "structured":
        title = "智能阅读器样本：结构化课程讲义"
        paragraphs = [
            ("1 研究目标", "Heading1"),
            ("本样本用于验证 DOCX 标题样式、页眉页脚、表格、脚注和分页边界。", None),
            ("1.1 阅读任务", "Heading2"),
            ("读者需要在长文档中定位定义、比较两项方案，并保存可回溯的原文证据。", None),
            ("2 约束条件", "Heading1"),
            ("The parser must preserve stable block identifiers and the original heading path.", None),
        ]
        rows = [["指标", "目标", "备注"], ["正文召回", ">= 0.95", "以人工参考文本为准"], ["引用定位", "页码 + 段落", "保留原文片段"]]
    elif variant == "meeting":
        title = "智能阅读器样本：会议记录"
        paragraphs = [
            ("会议主题", "Heading1"),
            ("本样本用于测试日期、编号、项目符号、表格和脱敏后的姓名占位符。", None),
            ("决议", "Heading1"),
            ("- 先完成本地解析；- 再比较检索结果；- 最后记录失败案例。", None),
            ("后续行动", "Heading2"),
            ("负责人 A 在 2026-09-30 前补充授权证明，负责人 B 复核表格字段。", None),
        ]
        rows = [["编号", "行动", "负责人", "截止日期"], ["A-01", "补充授权", "用户 A（脱敏）", "2026-09-30"], ["B-01", "复核字段", "用户 B（脱敏）", "2026-10-01"]]
    else:
        title = "智能阅读器样本：复杂方案记录"
        paragraphs = [
            ("摘要", "Heading1"),
            ("这是一个包含中英文混排、编号条款、表格和长段落的自制文档。", None),
            ("A. 数据处理流程", "Heading1"),
            ("输入文件经过格式识别、解析、结构归一化和证据定位。每一步都应保留可复现的配置。", None),
            ("A.1 失败处理", "Heading2"),
            ("当 OCR 置信度不足时，系统应保留原页图像，并把结果标记为需要人工核验。", None),
            ("B. 附录", "Heading1"),
            ("附录内容故意放在分页符之后，用于检查跨页段落和页脚处理。", None),
        ]
        rows = [["阶段", "输入", "输出", "风险"], ["解析", "原始文件", "结构块", "阅读顺序"], ["检索", "问题", "证据块", "召回不足"], ["回答", "证据", "引用回答", "无依据生成"]]

    document = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>",
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">",
        "<w:body>",
        paragraph_xml(title, "Title"),
    ]
    for text, style in paragraphs:
        document.append(paragraph_xml(text, style))
    document.append(table_xml(rows))
    if variant == "structured":
        document.append(paragraph_xml("脚注示例", "Heading2"))
        document.append("<w:p>正文中的脚注标记<w:r><w:footnoteReference w:id=\"1\"/></w:r>用于检查脚注是否被静默丢弃。</w:p>")
    document.append("<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>")
    document.append(paragraph_xml("分页后的附录", "Heading1"))
    document.append(paragraph_xml("此段位于显式分页符之后，不能与上一页的段落简单拼接。", None))
    document.append(
        "<w:sectPr><w:headerReference w:type=\"default\" r:id=\"rId2\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"/>"
        "<w:footerReference w:type=\"default\" r:id=\"rId3\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"/>"
        "<w:pgSz w:w=\"11906\" w:h=\"16838\"/><w:pgMar w:top=\"1440\" w:right=\"1440\" "
        "w:bottom=\"1440\" w:left=\"1440\"/></w:sectPr>"
    )
    document.append("</w:body></w:document>")

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>
</Types>"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    document_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/>
</Relationships>"""
    styles = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:uiPriority w:val="1"/><w:qFormat/><w:pPr><w:jc w:val="center"/></w:pPr><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/><w:outlineLvl w:val="0"/><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/><w:outlineLvl w:val="1"/><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
</w:styles>"""
    header = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>智能阅读器自制样本 | 页眉测试</w:t></w:r></w:p></w:hdr>"""
    footer = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>SELF-AUTHORED | footer reference</w:t></w:r></w:p></w:ftr>"""
    footnotes = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:footnote w:id="-1"><w:p/></w:footnote><w:footnote w:id="0"><w:p/></w:footnote><w:footnote w:id="1"><w:p><w:r><w:t>这是自制脚注，用于验证脚注元素和正文引用的关联。</w:t></w:r></w:p></w:footnote></w:footnotes>"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("word/document.xml", "".join(document))
        archive.writestr("word/_rels/document.xml.rels", document_rels)
        archive.writestr("word/styles.xml", styles)
        archive.writestr("word/header1.xml", header)
        archive.writestr("word/footer1.xml", footer)
        archive.writestr("word/footnotes.xml", footnotes)


def find_font() -> Path | None:
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def reportlab_font(font_path: Path):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    name = "SelfAuthoredFont"
    try:
        pdfmetrics.registerFont(TTFont(name, str(font_path), subfontIndex=0))
    except TypeError:
        pdfmetrics.registerFont(TTFont(name, str(font_path)))
    return name


def make_text_pdf(path: Path, two_columns: bool = False, profile: str = "basic") -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            BaseDocTemplate,
            Frame,
            FrameBreak,
            PageBreak,
            PageTemplate,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.pdfgen.canvas import Canvas
    except ImportError as exc:
        raise OptionalDependencyError("reportlab is required for text PDF generation") from exc
    font_path = find_font()
    if font_path is None:
        raise OptionalDependencyError("no Unicode font was found for PDF generation")
    font_name = reportlab_font(font_path)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SampleTitle", parent=styles["Title"], fontName=font_name, alignment=TA_CENTER, fontSize=18, leading=24))
    styles.add(ParagraphStyle(name="SampleHeading", parent=styles["Heading2"], fontName=font_name, fontSize=12, leading=16, spaceBefore=8))
    styles.add(ParagraphStyle(name="SampleBody", parent=styles["BodyText"], fontName=font_name, fontSize=9.5, leading=15))
    styles.add(ParagraphStyle(name="SampleFoot", parent=styles["BodyText"], fontName=font_name, fontSize=7.5, leading=10, textColor=colors.grey))

    def header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font_name, 7)
        canvas.drawString(18 * mm, 10 * mm, "SELF-AUTHORED PDF | physical page %d" % doc.page)
        canvas.drawRightString(192 * mm, 10 * mm, "header/footer and citation test")
        canvas.restoreState()

    def invariant_canvas(filename, **kwargs):
        # ReportLab otherwise embeds the current timestamp, changing the sample hash on every run.
        kwargs["invariant"] = 1
        return Canvas(filename, **kwargs)

    title = "智能阅读器自制 PDF 样本" if profile == "basic" else "智能阅读器自制 PDF：表格与公式"
    body = (
        "本样本包含中文、English terms、脚注提示和页眉页脚，用于验证正文、标题、段落、页码和引用定位。"
        if profile == "basic"
        else "本样本专门覆盖复杂表格、合并概念、公式文本和图注。公式示例：Recall@k = hits / k。"
    )
    table_data = (
        [["字段", "示例值", "风险"], ["physical_page", "2", "封面导致打印页码偏移"], ["heading_path", "1 > 2", "标题层级可能被误判"]]
        if profile == "basic"
        else [["指标", "公式/值", "解释"], ["Recall@k", "hits / k", "检索命中比例"], ["表格结构", "row + col", "合并单元格需保留"]]
    )
    table_widths = [38 * mm, 48 * mm, 65 * mm]
    if two_columns:
        # Keep the table within one column; the previous fixture overflowed its frame.
        table_widths = [20 * mm, 25 * mm, 37 * mm]
    story = [
        Paragraph(title, styles["SampleTitle"]),
        Spacer(1, 6 * mm),
        Paragraph("1 研究目标", styles["SampleHeading"]),
        Paragraph(body, styles["SampleBody"]),
        Paragraph("2 关键结论", styles["SampleHeading"]),
        Paragraph("解析结果不能只保留扁平纯文本。每个文本块还需要稳定 ID、标题路径、物理页码和原始位置。", styles["SampleBody"]),
        Table(table_data, colWidths=table_widths),
        Paragraph("脚注：这是一个可回溯的脚注占位，用来检查脚注是否被混入正文。", styles["SampleFoot"]),
    ]
    story[-2].setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("FONTNAME", (0, 0), (-1, -1), font_name), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    if two_columns:
        class TwoColumnDoc(BaseDocTemplate):
            pass

        path.parent.mkdir(parents=True, exist_ok=True)
        doc = TwoColumnDoc(str(path), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=16 * mm, bottomMargin=18 * mm)
        gap = 8 * mm
        width = (A4[0] - 30 * mm - gap) / 2
        column_height = A4[1] - 73 * mm
        frames = [
            Frame(15 * mm, A4[1] - 55 * mm, A4[0] - 30 * mm, 40 * mm, id="full-width-title"),
            Frame(15 * mm, 18 * mm, width, column_height, id="left"),
            Frame(15 * mm + width + gap, 18 * mm, width, column_height, id="right"),
        ]
        doc.addPageTemplates([PageTemplate(id="two", frames=frames, onPage=header_footer)])
        story.insert(1, Paragraph("跨栏标题和参考文献会故意让阅读顺序变得敏感。", styles["SampleBody"]))
        story.insert(2, FrameBreak())
        story.extend([
            Paragraph("左栏补充段落：阅读顺序应先完成当前栏，再进入同页另一栏；解析器不能把页脚插入正文。", styles["SampleBody"]),
            FrameBreak(),
            Paragraph("右栏内容", styles["SampleHeading"]),
            Paragraph("右栏补充段落：引用定位需要同时记录物理页码、文本块和坐标，表格应保持行列关系。", styles["SampleBody"]),
            Paragraph("3 参考文献", styles["SampleHeading"]),
            Paragraph("[1] A. Reader. Document provenance and evidence blocks. 2026.", styles["SampleBody"]),
            PageBreak(),
            Paragraph("4 第二页", styles["SampleHeading"]),
            Paragraph("第二页用于检查页码、跨页段落和引用位置。", styles["SampleBody"]),
        ])
        doc.build(story, canvasmaker=invariant_canvas)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
        doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer, canvasmaker=invariant_canvas)


def make_scan_pdf(path: Path) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise OptionalDependencyError("Pillow is required for scan PDF generation") from exc
    font_path = find_font()
    if font_path is None:
        raise OptionalDependencyError("no Unicode font was found for scan PDF generation")
    try:
        font = ImageFont.truetype(str(font_path), 34, index=0)
        small_font = ImageFont.truetype(str(font_path), 24, index=0)
    except OSError as exc:
        raise OptionalDependencyError(f"font cannot be loaded by Pillow: {font_path}") from exc
    pages = []
    for page_number in (1, 2):
        image = Image.new("RGB", (1654, 2339), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((65, 65, 1585, 2274), outline=(80, 80, 80), width=3)
        draw.text((125, 125), "扫描型中文样本 / OCR TEST", font=font, fill=(25, 25, 25))
        lines = [
            f"第 {page_number} 页  文档解析质量验证",
            "本页故意包含中文、English abbreviation、数字 12345 和全角标点。",
            "OCR 应保留物理页码，并标记可能存在的字符错误。",
            "表格区域： 解析器应至少保留行列关系或原图位置。",
            "注：页面略有倾斜，背景包含轻微噪声。",
        ]
        y = 260
        for line in lines:
            draw.text((135, y), line, font=small_font, fill=(35, 35, 35))
            y += 100
        draw.line((130, y + 20, 1450, y + 20), fill=(100, 100, 100), width=2)
        draw.text((135, y + 55), "A-01     0.95     表格候选单元格", font=small_font, fill=(45, 45, 45))
        draw.text((135, 2160), "扫描样本页脚 | page label: " + str(page_number), font=small_font, fill=(75, 75, 75))
        if page_number == 2:
            image = image.rotate(1.4, expand=True, fillcolor="white")
        pages.append(image)
    path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(path, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])


def make_markdown(path: Path) -> None:
    text = """# 智能阅读器 Markdown 自制样本

## 1 目的

本文件用于验证 **标题层级**、GFM 表格、代码块、脚注、数学公式、图片链接和中英文混排。

### 1.1 关键定义

稳定的 `block_id` 应该能回溯到原始段落，而不是只依赖检索结果中的文本片段。

## 2 指标表

| 指标 | 目标 | 说明 |
| --- | ---: | --- |
| 正文召回率 | 0.95 | 与人工参考文本比较 |
| 引用定位率 | 0.90 | 页码或行号可回溯 |

> 风险提示：表格、脚注和公式不能被静默删除。

```python
def locate(block_id: str) -> str:
    return f"evidence:{block_id}"
```

公式示例：$Recall@k = hits / k$。

![结构示意图](assets/layout-placeholder.png)

嵌套列表：

1. 文档导入
   1. 格式识别
   2. 原始文件哈希
2. 证据定位

脚注引用[^1] 应保留与正文的关联。

[^1]: 这是一个脚注，用于测试 GFM 扩展支持。
"""
    save_text(path, text.strip() + "\n")


def make_markdown_levels(path: Path) -> None:
    text = """# 多层目录与不规则标题

## 一级标题

正文段落位于标题之后。

#### 跳级标题

跳过了三级标题，用于检查解析器是否强行补齐层级。

### 回到三级

- 一级列表
  - 二级列表
    - 三级列表

> 引用块中的 `inline code` 仍然属于正文结构。
"""
    save_text(path, text.strip() + "\n")


def make_text_files(out: Path) -> None:
    utf8 = """智能阅读器纯文本样本

第一段包含中文、English、12345、全角标点，以及 / slash 和 — punctuation。
这一段很长，用于检查长行是否被错误拆分，以及换行归一化是否会改变证据位置。

第二段与第一段之间有一个空行。没有标题语法，段落边界只能依据换行和空行推断。
"""
    save_text(out / "txt" / "SELF-010-utf8.txt", utf8.strip() + "\n", newline="\r\n")
    gb_text = "历史编码样本\n本文件使用 GB18030 编码，包含中文标点、英文缩写 OCR 和旧式换行。\n"
    save_text(out / "txt" / "SELF-011-gb18030.txt", gb_text, encoding="gb18030", newline="\r\n")


def make_html(path: Path) -> None:
    document = """<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>网页快照样本</title><style>.ad{display:none}</style></head>
<body>
  <nav><a href="/">首页</a> <a href="/docs">文档</a> <a href="#method">方法</a></nav>
  <main>
    <article>
      <h1>网页快照：证据定位流程</h1>
      <p class="meta">版本 1.0 | 2026-09-23 | English label: provenance</p>
      <h2 id="method">方法</h2>
      <p>正文应与导航、广告和脚本分离。解析结果需要保留标题、段落、表格和原始链接。</p>
      <table><thead><tr><th>步骤</th><th>输出</th></tr></thead>
        <tbody><tr><td>解析</td><td>结构块</td></tr><tr><td>检索</td><td>证据块</td></tr></tbody>
      </table>
      <pre><code>document.querySelector('article')</code></pre>
    </article>
    <aside class="ad">这是应被识别为噪声的广告占位。</aside>
  </main>
  <footer>网页快照页脚 | 原始 URL 和抓取日期应另行登记</footer>
  <script>console.log('dynamic noise');</script>
</body></html>
"""
    save_text(path, document.strip() + "\n")


def make_annotations(out: Path) -> dict[str, dict[str, Any]]:
    annotations = {
        "SELF-008": {
            "fixed_queries": ["引用定位率", "block_id", "脚注"],
            "expected_evidence_fragments": ["稳定的 `block_id`", "引用定位率", "这是一个脚注"],
            "reference_notes": "标题路径应为 1 目的 > 1.1 关键定义，表格不应被当作普通段落。",
        },
        "SELF-009": {
            "fixed_queries": ["跳级标题", "三级列表", "inline code"],
            "expected_evidence_fragments": ["跳过了三级标题", "三级列表", "inline code"],
            "reference_notes": "标题层级出现 H2 -> H4 -> H3，不能静默重写为连续层级。",
        },
        "SELF-010": {
            "fixed_queries": ["长行", "段落边界", "全角标点"],
            "expected_evidence_fragments": ["这一段很长", "段落边界只能依据换行和空行推断"],
            "reference_notes": "保留 CRLF 的原始行号，同时提供规范化文本用于对照。",
        },
        "SELF-011": {
            "fixed_queries": ["GB18030", "旧式换行"],
            "expected_evidence_fragments": ["历史编码样本", "GB18030"],
            "reference_notes": "解析器不应在 UTF-8 解码失败后静默丢弃中文。",
        },
        "SELF-012": {
            "fixed_queries": ["证据定位流程", "结构块", "网页快照"],
            "expected_evidence_fragments": ["正文应与导航、广告和脚本分离", "解析", "检索"],
            "reference_notes": "导航、aside 广告和 script 应被分类或降权，不能与 article 正文混在一起。",
        },
        "SELF-005": {
            "fixed_queries": ["DOCX 标题样式", "引用定位", "正文中的脚注标记"],
            "expected_evidence_fragments": ["Heading 1/2/3", "稳定 block identifiers"],
            "reference_notes": "保留 Heading 样式、表格、脚注、页眉页脚和显式分页符。",
        },
        "SELF-006": {
            "fixed_queries": ["2026-09-30", "补充授权", "脱敏"],
            "expected_evidence_fragments": ["补充授权", "用户 A（脱敏）", "复核表格字段"],
            "reference_notes": "检查日期、行动项、负责人占位符和表格列语义。",
        },
        "SELF-003": {
            "fixed_queries": ["Recall@k", "合并单元格", "公式"],
            "expected_evidence_fragments": ["Recall@k", "合并单元格需保留"],
            "reference_notes": "表格和公式应保留为结构化候选或明确降级信息。",
        },
        "SELF-007": {
            "fixed_queries": ["失败处理", "跨页段落", "无依据生成"],
            "expected_evidence_fragments": ["OCR 置信度不足", "保留原页图像", "无依据生成"],
            "reference_notes": "检查复杂方案中的多级标题、长段落、表格和分页符。",
        },
        "SELF-001": {
            "fixed_queries": ["physical_page", "heading_path", "脚注"],
            "expected_evidence_fragments": ["物理页码", "标题路径", "脚注占位"],
            "reference_notes": "单栏 PDF 的文本顺序应稳定，页脚不应被误当正文。",
        },
        "SELF-002": {
            "fixed_queries": ["跨栏标题", "参考文献", "阅读顺序"],
            "expected_evidence_fragments": ["跨栏标题和参考文献", "第二页用于检查页码"],
            "reference_notes": "比较默认顺序与按栏顺序的差异，并保留页码。",
        },
        "SELF-004": {
            "fixed_queries": ["OCR TEST", "物理页码", "低清"],
            "expected_evidence_fragments": ["OCR 应保留物理页码", "表格区域"],
            "reference_notes": "这是图像型 PDF，不应依赖已有文本层；保存页面截图和 OCR 置信度。",
        },
    }
    for sample_id, annotation in annotations.items():
        annotation.update({"sample_id": sample_id, "annotation_version": 1, "source": "project-authored"})
        save_text(out / "annotations" / f"{sample_id}.json", json.dumps(annotation, ensure_ascii=False, indent=2) + "\n")
    return annotations


def build_manifest(out: Path, annotations: dict[str, dict[str, Any]], skipped: list[str]) -> Path:
    today = dt.date.today().isoformat()
    definitions = [
        ("SELF-008", out / "markdown" / "SELF-008-complex.md", "MD", "Markdown", ["GFM table", "code block", "footnote", "formula", "image link", "nested list"], ["dialect extensions", "asset link"]),
        ("SELF-009", out / "markdown" / "SELF-009-heading-levels.md", "MD", "Markdown", ["heading level gap", "nested list", "blockquote", "inline code"], ["heading normalization", "list nesting"]),
        ("SELF-010", out / "txt" / "SELF-010-utf8.txt", "TXT", "TXT", ["UTF-8", "CRLF", "long line", "blank line", "mixed language"], ["paragraph boundary", "line normalization"]),
        ("SELF-011", out / "txt" / "SELF-011-gb18030.txt", "TXT", "TXT", ["GB18030", "CRLF", "Chinese punctuation"], ["encoding detection", "replacement characters"]),
        ("SELF-012", out / "html" / "SELF-012-noisy.html", "HTML", "HTML snapshot", ["navigation", "article", "table", "script", "ad noise", "footer"], ["content extraction", "dynamic noise"]),
        ("SELF-005", out / "docx" / "SELF-005-structured.docx", "DOCX", "DOCX", ["Heading 1/2", "table", "header", "footer", "footnote", "page break"], ["style mapping", "pagination"]),
        ("SELF-006", out / "docx" / "SELF-006-meeting-notes.docx", "DOCX", "DOCX", ["date", "action table", "bullets", "redacted names"], ["list extraction", "table semantics"]),
        ("SELF-007", out / "docx" / "SELF-007-complex.docx", "DOCX", "DOCX", ["multilingual", "table", "long paragraph", "page break", "footnote"], ["structure loss", "cross-page paragraph"]),
        ("SELF-001", out / "pdf" / "SELF-001-single-column.pdf", "PDF text", "PDF text", ["single column", "header", "footer", "footnote", "table", "page number"], ["reading order", "printed page label"]),
        ("SELF-003", out / "pdf" / "SELF-003-table-formula.pdf", "PDF text", "PDF text", ["table", "formula", "figure caption", "mixed language"], ["table structure", "formula extraction"]),
        ("SELF-002", out / "pdf" / "SELF-002-two-column.pdf", "PDF text", "PDF text", ["two columns", "cross-column heading", "references", "table"], ["column order", "citation bbox"]),
        ("SELF-004", out / "pdf" / "SELF-004-scanned.pdf", "PDF scan", "PDF scan", ["image-only", "Chinese OCR", "English abbreviation", "tilt", "noise"], ["OCR CER", "low confidence"]),
    ]
    rows = []
    for sample_id, path, format_name, source_format, features, risks in definitions:
        if not path.exists():
            continue
        raw = path.read_bytes()
        line_count = raw.count(b"\n")
        page_count = None
        if path.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader
                page_count = len(PdfReader(str(path)).pages)
            except Exception:
                page_count = None
        rows.append({
            "sample_id": sample_id,
            "path": path.relative_to(out.parent.parent).as_posix(),
            "source": "project-authored",
            "license_or_authorization": "project-authored; no third-party content",
            "format": format_name,
            "bytes": len(raw),
            "pages": page_count,
            "line_count": line_count,
            "char_count_utf8": len(raw.decode("utf-8", errors="replace")),
            "sha256": sha256(path),
            "languages": ["Chinese", "English"],
            "layout_features": features,
            "expected_risks": risks,
            "cloud_upload_allowed": "no",
            "generated_on": today,
            "generator_version": SCRIPT_VERSION,
            "annotation": f"annotations/{sample_id}.json" if sample_id in annotations else None,
        })
    manifest = {
        "manifest_version": 1,
        "generated_on": today,
        "generator": "generate_self_authored_samples.py",
        "license_or_authorization_default": "project-authored; no third-party content",
        "cloud_upload_allowed_default": "no",
        "samples": rows,
        "skipped_optional_outputs": skipped,
        "notes": [
            "These samples are controlled fixtures, not evidence that a parser supports all real-world documents.",
            "Keep source files and annotations together; do not silently normalize or overwrite the originals.",
        ],
    }
    manifest_path = out / "self-authored-manifest.json"
    save_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest_path


def generate(output: Path, strict: bool) -> int:
    output.mkdir(parents=True, exist_ok=True)
    skipped: list[str] = []
    make_markdown(output / "markdown" / "SELF-008-complex.md")
    make_markdown_levels(output / "markdown" / "SELF-009-heading-levels.md")
    make_text_files(output)
    make_html(output / "html" / "SELF-012-noisy.html")
    make_docx(output / "docx" / "SELF-005-structured.docx", "structured")
    make_docx(output / "docx" / "SELF-006-meeting-notes.docx", "meeting")
    make_docx(output / "docx" / "SELF-007-complex.docx", "complex")

    optional_generators = [
        ("SELF-001-single-column.pdf", lambda path: make_text_pdf(path, two_columns=False)),
        ("SELF-003-table-formula.pdf", lambda path: make_text_pdf(path, two_columns=False, profile="table_formula")),
        ("SELF-002-two-column.pdf", lambda path: make_text_pdf(path, two_columns=True)),
        ("SELF-004-scanned.pdf", make_scan_pdf),
    ]
    for filename, generator in optional_generators:
        try:
            generator(output / "pdf" / filename)
        except OptionalDependencyError as exc:
            skipped.append(f"{filename}: {exc}")
            if strict:
                raise
            print(f"WARNING: skipped {filename}: {exc}", file=sys.stderr)

    annotations = make_annotations(output)
    manifest = build_manifest(output, annotations, skipped)
    print(f"Generated {len(json.loads(manifest.read_text(encoding='utf-8'))['samples'])} samples")
    print(f"Manifest: {manifest}")
    if skipped:
        print("Skipped optional outputs:")
        for item in skipped:
            print(f"  - {item}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output directory for generated samples")
    parser.add_argument("--strict", action="store_true", help="fail when PDF dependencies or fonts are unavailable")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(generate(args.output.resolve(), args.strict))
