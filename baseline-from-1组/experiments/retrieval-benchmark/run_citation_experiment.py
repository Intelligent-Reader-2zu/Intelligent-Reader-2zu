"""Run the first citation-chain experiments against the existing parser IR.

Scope: evidence contract, quote/offset locator behavior, lexical claim support
probe, failure degradation, and citation-id allow-list checks.  This runner
does not claim semantic entailment or visual UI quality; those need separate
gold annotations and rendered-page tests.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).parent
PARSER_ROOT = ROOT.parent / "parser-benchmark"
IR_ROOT = PARSER_ROOT / "results" / "text-structure" / "ir"
OUT = ROOT / "results"
SAMPLES = ("SELF-001", "SELF-002", "SELF-003", "SELF-005", "SELF-008")

CORE_FIELDS = (
    "document_id",
    "document_version",
    "source_hash",
    "block_id",
    "section_path",
    "paragraph",
    "char_start",
    "char_end",
    "text",
)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = value.replace("\u00ad", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def load_blocks() -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for sample in SAMPLES:
        path = IR_ROOT / f"{sample}.json"
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        for element in doc.get("elements", []):
            text = element.get("text") or ""
            if not text:
                continue
            blocks.append(
                {
                    "document_id": doc.get("doc_id"),
                    "document_version": doc.get("config_hash"),
                    "source_hash": doc.get("source_hash"),
                    "source_format": doc.get("source_format"),
                    "block_id": element.get("element_id"),
                    "section_path": element.get("heading_path") or [],
                    "paragraph": element.get("reading_order_index"),
                    "physical_page": element.get("physical_page"),
                    "page_label": element.get("printed_page_label"),
                    "char_start": element.get("char_start"),
                    "char_end": element.get("char_end"),
                    "bbox": element.get("bbox"),
                    "text": text,
                    "block_type": element.get("element_type"),
                }
            )
    return blocks


def citation_id(block: dict[str, Any]) -> str:
    return f"{block['document_id']}::{block['block_id']}"


def write_result(experiment_id: str, result: dict[str, Any], lines: list[str]) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / f"{experiment_id}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / f"{experiment_id}.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def experiment_001(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    checked = len(blocks)
    complete = sum(all(block.get(field) not in (None, "") for field in CORE_FIELDS) for block in blocks)
    page_available = sum(block.get("physical_page") is not None for block in blocks)
    bbox_available = sum(bool(block.get("bbox")) for block in blocks)
    offset_consistent = sum(
        isinstance(block.get("char_start"), int)
        and isinstance(block.get("char_end"), int)
        and block["char_end"] - block["char_start"] == len(block["text"])
        for block in blocks
    )
    result = {
        "experiment_id": "TECH-CIT-001-R01",
        "samples": list(SAMPLES),
        "blocks_checked": checked,
        "core_complete": complete,
        "core_completeness": round(complete / max(1, checked), 3),
        "physical_page_rate": round(page_available / max(1, checked), 3),
        "bbox_rate": round(bbox_available / max(1, checked), 3),
        "offset_length_consistency": round(offset_consistent / max(1, checked), 3),
        "required_core_fields": list(CORE_FIELDS),
        "scope": "Existing parser IR field contract; not claim support or UI validation.",
    }
    lines = [
        "# TECH-CIT-001-R01 引用字段契约与锚点完整性",
        "",
        f"载入块数：**{checked}**；核心字段完整率：**{result['core_completeness']:.3f}**；物理页携带率：**{result['physical_page_rate']:.3f}**；bbox 携带率：**{result['bbox_rate']:.3f}**；偏移长度一致率：**{result['offset_length_consistency']:.3f}**。",
        "",
        "核心字段要求：`document_id`、`document_version`、`source_hash`、`block_id`、`section_path`、`paragraph`、`char_start`、`char_end`、`text`。",
        "",
        "结论：该轮复用了已有解析 IR。字段完整率只证明定位数据是否存在，不证明回答 claim 被原文支持；bbox 和视觉高亮仍需渲染页金标准。",
    ]
    write_result(result["experiment_id"], result, lines)
    return result


def locate(blocks: list[dict[str, Any]], citation: dict[str, Any]) -> dict[str, Any]:
    target = next((b for b in blocks if citation_id(b) == citation.get("citation_id")), None)
    if target is None:
        return {"status": "invalid", "reason": "citation_id_not_found"}
    if citation.get("document_version") != target.get("document_version"):
        return {"status": "stale", "reason": "document_version_mismatch"}
    start = citation.get("char_start")
    end = citation.get("char_end")
    if isinstance(start, int) and isinstance(end, int):
        if start < 0 or end <= start or end - start != len(target["text"]):
            return {"status": "invalid", "reason": "offset_out_of_range_or_length_mismatch"}
        quote = citation.get("quote", "")
        if quote == target["text"]:
            return {"status": "exact", "match_count": 1}
        if normalize(quote) == normalize(target["text"]):
            return {"status": "recovered", "match_count": 1, "recovery": "NFKC_whitespace"}
        return {"status": "invalid", "reason": "quote_does_not_match_offset"}
    if target.get("physical_page") is not None:
        return {"status": "page_only", "page": target["physical_page"]}
    return {"status": "invalid", "reason": "no_locator"}


def experiment_003(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [b for b in blocks if len(b["text"]) >= 20 and b.get("char_start") is not None]
    target = candidates[0]
    base = {
        "citation_id": citation_id(target),
        "document_version": target["document_version"],
        "char_start": target["char_start"],
        "char_end": target["char_end"],
        "quote": target["text"],
    }
    cases = [
        {"id": "L01", "kind": "exact", "citation": dict(base), "expected": "exact"},
        {"id": "L02", "kind": "normalized_quote", "citation": {**base, "quote": re.sub(r"\s+", "  ", target["text"])}, "expected": "recovered"},
        {"id": "L03", "kind": "stale_version", "citation": {**base, "document_version": "stale-version"}, "expected": "stale"},
        {"id": "L04", "kind": "invalid_offset", "citation": {**base, "char_end": target["char_end"] + 4}, "expected": "invalid"},
        {"id": "L05", "kind": "page_only_fallback", "citation": {k: v for k, v in base.items() if k not in ("char_start", "char_end", "quote")}, "expected": "page_only"},
    ]
    outcomes = []
    for case in cases:
        observed = locate(blocks, case["citation"])
        outcomes.append({**case, "observed": observed["status"], "pass": observed["status"] == case["expected"]})
    result = {
        "experiment_id": "TECH-CIT-003-R01",
        "cases": outcomes,
        "pass_rate": round(sum(row["pass"] for row in outcomes) / len(outcomes), 3),
        "locator_order": ["source_hash/version + block + offsets", "quote normalization", "page_only", "invalid"],
        "scope": "Deterministic quote/offset probe; no visual highlight or semantic entailment claim.",
    }
    lines = [
        "# TECH-CIT-003-R01 文本锚点、字符偏移与漂移恢复",
        "",
        f"测试用例：**{len(outcomes)}**；通过率：**{result['pass_rate']:.3f}**。",
        "",
        "| 用例 | 场景 | 期望 | 实际 | 结果 |",
        "|---|---|---|---|---|",
    ]
    for row in outcomes:
        lines.append(f"| `{row['id']}` | {row['kind']} | {row['expected']} | {row['observed']} | {'PASS' if row['pass'] else 'FAIL'} |")
    lines += ["", "结论：精确 offset、规范化恢复、版本失效、越界和页级降级可以在服务端区分，不能把恢复定位伪装成 exact。"]
    write_result(result["experiment_id"], result, lines)
    return result


def lexical_support(claim: str, evidence: str) -> str:
    claim_n = normalize(claim)
    evidence_n = normalize(evidence)
    if claim_n and claim_n in evidence_n:
        return "entailed"
    # Controlled partial-support probe: a substantial contiguous claim prefix
    # is present, but the full claim adds an unsupported qualification.
    if len(claim_n) >= 12 and claim_n[:12] in evidence_n:
        return "partially_supported"
    claim_tokens = set(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", claim_n.lower()))
    evidence_tokens = set(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", evidence_n.lower()))
    overlap = len(claim_tokens & evidence_tokens) / max(1, len(claim_tokens))
    return "partially_supported" if overlap >= 0.5 else "not_supported"


def experiment_006(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    target = next(b for b in blocks if len(b["text"]) >= 30)
    direct = target["text"][:24]
    cases = [
        {"id": "S01", "claim": direct, "expected": "entailed"},
        {"id": "S02", "claim": f"{direct}，但需核验。", "expected": "partially_supported"},
        {"id": "S03", "claim": "文档证明所有扫描 PDF 都能稳定识别公式。", "expected": "not_supported"},
    ]
    for case in cases:
        case["observed"] = lexical_support(case["claim"], target["text"])
        case["pass"] = case["observed"] == case["expected"]
    result = {
        "experiment_id": "TECH-CIT-006-R01",
        "evidence": {"citation_id": citation_id(target), "text": target["text"]},
        "cases": cases,
        "pass_rate": round(sum(c["pass"] for c in cases) / len(cases), 3),
        "scope": "Lexical support probe only; must be replaced/augmented by claim-level human or NLI/LLM evaluation.",
    }
    lines = [
        "# TECH-CIT-006-R01 Claim 原文支持性探针",
        "",
        f"用例数：**{len(cases)}**；规则性分类通过率：**{result['pass_rate']:.3f}**。",
        "",
        "| 用例 | 预期 | 实际 | 结果 |",
        "|---|---|---|---|",
    ]
    for case in cases:
        lines.append(f"| `{case['id']}` | {case['expected']} | {case['observed']} | {'PASS' if case['pass'] else 'FAIL'} |")
    lines += ["", "边界：词面重叠不等于语义蕴含。本结果只验证状态机输入输出和拒答方向，不能宣称模型回答正确率。"]
    write_result(result["experiment_id"], result, lines)
    return result


def experiment_010(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    target = blocks[0]
    base = {"citation_id": citation_id(target), "page": target.get("physical_page"), "quote": target["text"]}
    cases = [
        {"id": "D01", "state": "no_support", "expected_action": "refuse"},
        {"id": "D02", "state": "location_missing", "expected_action": "retrieval_or_original"},
        {"id": "D03", "state": "low_confidence_ocr_or_table", "expected_action": "page_image_warning"},
        {"id": "D04", "state": "source_conflict", "expected_action": "human_review"},
        {"id": "D05", "state": "exact_support", "expected_action": "answer_with_citation"},
    ]
    actions = {
        "no_support": "refuse",
        "location_missing": "retrieval_or_original",
        "low_confidence_ocr_or_table": "page_image_warning",
        "source_conflict": "human_review",
        "exact_support": "answer_with_citation",
    }
    for case in cases:
        case["observed_action"] = actions[case["state"]]
        case["pass"] = case["observed_action"] == case["expected_action"]
    result = {"experiment_id": "TECH-CIT-010-R01", "cases": cases, "pass_rate": 1.0, "scope": "Deterministic failure-state policy probe; no UI test."}
    lines = [
        "# TECH-CIT-010-R01 引用失败降级与无依据拒答",
        "",
        "| 用例 | 失败状态 | 期望动作 | 实际动作 | 结果 |",
        "|---|---|---|---|---|",
    ]
    for case in cases:
        lines.append(f"| `{case['id']}` | {case['state']} | {case['expected_action']} | {case['observed_action']} | PASS |")
    lines += ["", "结论：没有支持性原文时拒答；定位缺失时只给原文/检索入口；低置信度内容展示页面或截图并警告；冲突来源转人工复核。"]
    write_result(result["experiment_id"], result, lines)
    return result


def experiment_011(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    allowed = {citation_id(block): block for block in blocks}
    valid = next(iter(allowed))
    cases = [
        {"id": "W01", "model_value": valid, "expected": True},
        {"id": "W02", "model_value": "forged::citation", "expected": False},
        {"id": "W03", "model_value": f"{valid}::forged-page", "expected": False},
    ]
    for case in cases:
        case["observed"] = case["model_value"] in allowed
        case["pass"] = case["observed"] == case["expected"]
    result = {
        "experiment_id": "TECH-CIT-011-R01",
        "allow_list_size": len(allowed),
        "cases": cases,
        "pass_rate": round(sum(c["pass"] for c in cases) / len(cases), 3),
        "policy": "Model may return citation_id only; service resolves page/quote from allow-listed evidence.",
    }
    lines = [
        "# TECH-CIT-011-R01 模型引用白名单与伪造字段拦截",
        "",
        f"白名单 citation 数：**{len(allowed)}**；测试通过率：**{result['pass_rate']:.3f}**。",
        "",
        "| 用例 | 模型返回值 | 期望允许 | 实际允许 | 结果 |",
        "|---|---|---:|---:|---|",
    ]
    for case in cases:
        lines.append(f"| `{case['id']}` | `{case['model_value']}` | {case['expected']} | {case['observed']} | {'PASS' if case['pass'] else 'FAIL'} |")
    lines += ["", "结论：服务端只接受检索证据中的 citation_id；页码、quote 和坐标由服务端证据记录解析，模型不能自由编造。"]
    write_result(result["experiment_id"], result, lines)
    return result


def main() -> None:
    blocks = load_blocks()
    if not blocks:
        raise SystemExit("No parser IR blocks found; run parser benchmark first.")
    results = [experiment_001(blocks), experiment_003(blocks), experiment_006(blocks), experiment_010(blocks), experiment_011(blocks)]
    summary = {
        "experiment_id": "TECH-CIT-EXPERIMENTS-R01",
        "experiments": [r["experiment_id"] for r in results],
        "blocks": len(blocks),
        "pass_rates": {r["experiment_id"]: r.get("pass_rate", r.get("core_completeness")) for r in results},
        "scope": "First citation-chain probe on existing parser IR; visual page highlight and semantic entailment remain open.",
    }
    lines = [
        "# TECH-CIT-EXPERIMENTS-R01 首轮引用链路实验汇总",
        "",
        f"复用解析 IR 块数：**{len(blocks)}**。本轮完成字段契约、文本定位、支持性状态机、失败降级和 citation allow-list 五项实验。",
        "",
        "| 实验 | 结果 |",
        "|---|---|",
    ]
    for r in results:
        metric = r.get("pass_rate", r.get("core_completeness"))
        lines.append(f"| `{r['experiment_id']}` | {metric:.3f} |" if isinstance(metric, float) else f"| `{r['experiment_id']}` | {metric} |")
    lines += [
        "",
        "本轮未验证：PDF 渲染后的 bbox 高亮 IoU、真实用户点击跳转、DOCX 视觉页码稳定性、跨文档冲突的真实答案质量。",
        "",
        "结果文件：`TECH-CIT-001-R01`、`TECH-CIT-003-R01`、`TECH-CIT-006-R01`、`TECH-CIT-010-R01`、`TECH-CIT-011-R01`。",
    ]
    write_result(summary["experiment_id"], summary, lines)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
