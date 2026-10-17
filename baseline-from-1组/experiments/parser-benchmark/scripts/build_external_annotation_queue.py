"""Build an unlabeled annotation queue from the external sample inventory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "results" / "text-structure" / "external-inventory.json"
OUT_JSON = ROOT / "results" / "text-structure" / "external-annotation-queue.json"
OUT_MD = ROOT / "results" / "text-structure" / "EXTERNAL-ANNOTATION-QUEUE.md"
SELECTED = {"OPEN-003", "OPEN-010", "OPEN-011", "WEB-001", "WEB-002", "WEB-004"}


def pdf_queue(path: Path) -> dict[str, Any]:
    import fitz

    with fitz.open(path) as document:
        pages = []
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text") or ""
            pages.append(
                {
                    "physical_page": page_number,
                    "text_chars": len(text),
                    "block_count": len(page.get_text("blocks")),
                    "image_count": len(page.get_images(full=True)),
                    "text_preview": " ".join(text.split())[:220],
                }
            )
        candidates: list[dict[str, Any]] = []
        seen: set[int] = set()

        def add(page_number: int, reason: str) -> None:
            if page_number < 1 or page_number > len(pages) or page_number in seen:
                return
            seen.add(page_number)
            page = pages[page_number - 1].copy()
            page["reason"] = reason
            page["annotation_fields"] = {
                "reading_order_rank": "fill",
                "units": "fill label/text/bbox/heading_level/paragraph_id",
                "table_grids": "fill if table appears",
                "uncertainties": "fill when visual evidence is ambiguous",
            }
            candidates.append(page)

        add(1, "opening page; verify cover, title, header/footer and first reading order")
        if pages:
            add(max(pages, key=lambda item: item["text_chars"])["physical_page"], "maximum text density; inspect paragraph boundaries and columns")
            add(max(pages, key=lambda item: item["block_count"])["physical_page"], "maximum text block count; inspect fragmentation and reading order")
            add(max(pages, key=lambda item: item["image_count"])["physical_page"], "maximum image count; inspect figures, captions and nearby text")
        return {"kind": "PDF", "page_count": len(pages), "candidate_pages": candidates}


def css_path(element: Any) -> str:
    parts = []
    current = element
    while current is not None and getattr(current, "name", None) not in {None, "[document]"}:
        name = current.name
        if current.get("id"):
            # Attribute selectors remain valid when an HTML id contains CSS punctuation.
            escaped_id = str(current["id"]).replace("\\", "\\\\").replace('"', '\\"')
            parts.append(f'{name}[id="{escaped_id}"]')
            break
        parent = current.parent
        if parent is None:
            parts.append(name)
            break
        siblings = [child for child in parent.find_all(name, recursive=False)]
        index = siblings.index(current) + 1 if current in siblings else 1
        parts.append(f"{name}:nth-of-type({index})")
        current = parent
    return " > ".join(reversed(parts))


def html_queue(path: Path) -> dict[str, Any]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    candidates = []
    seen: set[str] = set()

    def add(element: Any, reason: str) -> None:
        selector = css_path(element)
        if selector in seen:
            return
        seen.add(selector)
        candidates.append(
            {
                "selector": selector,
                "tag": element.name,
                "text_preview": " ".join(element.get_text(" ", strip=True).split())[:220],
                "reason": reason,
                "annotation_fields": {
                    "heading_level": "fill for headings only",
                    "role": "fill body/navigation/advertisement/code/table/caption/reference",
                    "parent_selector": "fill",
                    "relations": "fill caption/reference/anchor relations",
                },
            }
        )

    first_h1 = soup.find("h1")
    if first_h1:
        add(first_h1, "first h1; verify document title and root heading")
    first_h2 = soup.find("h2")
    if first_h2:
        add(first_h2, "first h2; verify heading path and navigation contamination")
    for heading in soup.find_all(["h2", "h3", "h4"]):
        text = " ".join(heading.get_text(" ", strip=True).split()).casefold()
        if "reference" in text or "bibliograph" in text:
            add(heading, "reference section candidate; verify citation boundary")
            break
    first_table = soup.find("table")
    if first_table:
        add(first_table, "first table; verify table role, caption and cell structure")
    first_code = soup.find(["pre", "code"])
    if first_code:
        add(first_code, "first code candidate; verify code block boundary")
    article = soup.find("article")
    if article:
        add(article, "article candidate; verify正文与导航/脚本边界")
    return {"kind": "HTML", "candidate_nodes": candidates}


def main() -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    queue = []
    for sample in inventory["samples"]:
        if sample.get("sample_id") not in SELECTED or sample.get("status") != "ok":
            continue
        path = Path(sample["path"])
        item = {
            "sample_id": sample["sample_id"],
            "source_url": sample.get("source_url"),
            "source_sha256": sample.get("actual_sha256"),
            "license_or_authorization": sample.get("license_or_authorization"),
            "cloud_upload_allowed": sample.get("cloud_upload_allowed"),
            "path": str(path),
            "review_status": "draft",
        }
        item["queue"] = pdf_queue(path) if path.suffix.lower() == ".pdf" else html_queue(path)
        queue.append(item)
    report = {
        "experiment_id": "TECH-STRUCT-013-R01",
        "scope": "unlabeled external annotation queue",
        "samples": queue,
        "boundary": "Candidate locations only; no predicted labels, gold annotations, license approval, or accuracy score.",
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# 外部样本人工标注队列",
        "",
        "此文件只列出候选页码/DOM 位置，不包含标题层级、阅读顺序或正文角色金标准。标注前必须查看原始 PDF 页面或 HTML 快照。",
        "",
    ]
    for sample in queue:
        lines.extend([f"## {sample['sample_id']}", f"来源：{sample.get('source_url')}", f"SHA-256：`{sample.get('source_sha256')}`", ""])
        if sample["queue"]["kind"] == "PDF":
            lines.append("| 页码 | 文本字符 | 块数 | 图片数 | 选择原因 |")
            lines.append("|---:|---:|---:|---:|---|")
            for page in sample["queue"]["candidate_pages"]:
                lines.append(f"| {page['physical_page']} | {page['text_chars']} | {page['block_count']} | {page['image_count']} | {page['reason']} |")
        else:
            lines.append("| DOM selector | 标签 | 选择原因 |")
            lines.append("|---|---|---|")
            for node in sample["queue"]["candidate_nodes"]:
                lines.append(f"| `{node['selector']}` | `{node['tag']}` | {node['reason']} |")
        lines.extend(["", "标注状态：`draft`", ""])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"experiment_id": report["experiment_id"], "sample_count": len(queue), "json": str(OUT_JSON), "markdown": str(OUT_MD)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
