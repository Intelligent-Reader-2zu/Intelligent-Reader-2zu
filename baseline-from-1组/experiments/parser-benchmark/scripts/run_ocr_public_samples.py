from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import statistics
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

from PIL import Image
from rapidocr import RapidOCR

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from run_ocr_rapidocr import run_page as run_rapidocr_page  # noqa: E402
from run_ocr_tesseract_matrix import run_tesseract  # noqa: E402


ROOT = SCRIPT_DIR.parent
DEFAULT_SAMPLE_ROOT = ROOT / "samples/public-ocr"
DEFAULT_MANIFEST = DEFAULT_SAMPLE_ROOT / "manifest.json"
DEFAULT_QUESTIONS = DEFAULT_SAMPLE_ROOT / "public-ocr-questions.json"
DEFAULT_OUTPUT = ROOT / "results/ocr-public-samples"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(text: str) -> str:
    return "".join(unicodedata.normalize("NFKC", text).lower().split())


def nearest_percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(percentile * len(ordered) + 0.999999) - 1))
    return ordered[index]


def question_result(question: dict, text: str, lines: list[str], capabilities: dict) -> dict:
    required = question.get("must_contain", [])
    normalized_text = normalize(text)
    document_hits = {token: normalize(token) in normalized_text for token in required}
    if question["match"] == "document":
        passed = all(document_hits.values())
        matched_line = None
    elif question["match"] == "same_line":
        matched_line = next(
            (line for line in lines if all(normalize(token) in normalize(line) for token in required)),
            None,
        )
        passed = matched_line is not None
    elif question["match"] == "capability":
        capability = question["required_capability"]
        passed = bool(capabilities.get(capability, False))
        matched_line = None
    else:
        raise ValueError(f"unsupported question match mode: {question['match']}")
    return {
        "question_id": question["id"],
        "match": question["match"],
        "passed": passed,
        "document_hits": document_hits,
        "matched_line": matched_line,
        "required_capability": question.get("required_capability"),
    }


def engine_result(
    engine_name: str,
    image_path: Path,
    rapid_engine: RapidOCR,
    repeats: int,
) -> dict:
    runs_ms: list[float] = []
    text = ""
    items: list[dict] = []
    stderr = ""
    for run_index in range(repeats):
        if engine_name == "rapidocr":
            current_text, current_items, elapsed_ms = run_rapidocr_page(rapid_engine, image_path)
            current_stderr = ""
        elif engine_name == "tesseract":
            current_text, current_items, elapsed_ms, current_stderr = run_tesseract(
                image_path, "chi_sim+eng", 3
            )
        else:
            raise ValueError(engine_name)
        runs_ms.append(elapsed_ms)
        if run_index == 0:
            text = current_text
            items = current_items
            stderr = current_stderr

    confidences = [float(item["confidence"]) for item in items]
    capabilities = {
        "formula_structure": False,
        "table_structure": False,
        "seal_region_class": False,
        "word_or_line_bbox": bool(items),
    }
    return {
        "status": "succeeded",
        "text": text,
        "lines": text.splitlines(),
        "items": items,
        "run_ms": runs_ms,
        "latency_ms_p50": statistics.median(runs_ms),
        "latency_ms_p95": nearest_percentile(runs_ms, 0.95),
        "mean_confidence": statistics.mean(confidences) if confidences else None,
        "low_confidence_item_ratio": (
            sum(value < 60 for value in confidences) / len(confidences) if confidences else None
        ),
        "bbox_item_ratio": (
            sum(bool(item.get("bbox")) for item in items) / len(items) if items else None
        ),
        "capabilities": capabilities,
        "stderr": stderr.strip(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-root", type=Path, default=DEFAULT_SAMPLE_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    sample_root = args.sample_root.resolve()
    manifest = json.loads(args.manifest.resolve().read_text(encoding="utf-8"))
    questions_doc = json.loads(args.questions.resolve().read_text(encoding="utf-8"))
    output_root = args.output.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    questions_by_sample: dict[str, list[dict]] = {}
    for question in questions_doc["questions"]:
        questions_by_sample.setdefault(question["sample_id"], []).append(question)

    rapid_init_started = time.perf_counter()
    rapid_engine = RapidOCR()
    rapid_init_ms = (time.perf_counter() - rapid_init_started) * 1000
    tesseract_version = subprocess.run(
        ["tesseract", "--version"], capture_output=True, check=True, text=True, encoding="utf-8"
    ).stdout.splitlines()[0]

    sample_results = []
    for sample in manifest["samples"]:
        if not sample.get("included"):
            continue
        image_path = sample_root / sample["file"]
        actual_hash = sha256(image_path)
        if actual_hash != sample["sha256"]:
            raise SystemExit(
                f"source hash mismatch for {sample['id']}: expected {sample['sha256']}, actual {actual_hash}"
            )
        with Image.open(image_path) as image:
            dimensions = [image.width, image.height]
        per_engine = {}
        for engine_name in ("rapidocr", "tesseract"):
            try:
                result = engine_result(engine_name, image_path, rapid_engine, args.repeats)
                result["questions"] = [
                    question_result(
                        question,
                        result["text"],
                        result["lines"],
                        result["capabilities"],
                    )
                    for question in questions_by_sample.get(sample["id"], [])
                ]
            except Exception as exc:
                result = {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "questions": [
                        {
                            "question_id": question["id"],
                            "passed": False,
                            "error": "engine_failed",
                        }
                        for question in questions_by_sample.get(sample["id"], [])
                    ],
                }
            per_engine[engine_name] = result
            engine_dir = output_root / engine_name
            engine_dir.mkdir(parents=True, exist_ok=True)
            (engine_dir / f"{sample['id']}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        sample_results.append(
            {
                "sample_id": sample["id"],
                "file": sample["file"],
                "sha256": actual_hash,
                "dimensions": dimensions,
                "features": sample["features"],
                "engines": per_engine,
            }
        )

    control = next(item for item in manifest["samples"] if item["id"] == "PUB-OCR-CTRL-001")
    control_path = sample_root / control["file"]
    import fitz

    document = fitz.open(control_path)
    text_lengths = [len(page.get_text("text").strip()) for page in document]
    text_layer_control = {
        "sample_id": control["id"],
        "sha256": sha256(control_path),
        "page_count": len(document),
        "page_text_lengths": text_lengths,
        "has_usable_text_layer": any(length >= 20 for length in text_lengths),
        "decision": "skip_ocr" if any(length >= 20 for length in text_lengths) else "run_ocr",
    }

    aggregate = {}
    for engine_name in ("rapidocr", "tesseract"):
        engine_samples = [item["engines"][engine_name] for item in sample_results]
        succeeded = [item for item in engine_samples if item["status"] == "succeeded"]
        latencies = [value for item in succeeded for value in item["run_ms"]]
        questions = [question for item in engine_samples for question in item["questions"]]
        aggregate[engine_name] = {
            "sample_success_rate": len(succeeded) / len(engine_samples),
            "latency_ms_p50": statistics.median(latencies) if latencies else None,
            "latency_ms_p95": nearest_percentile(latencies, 0.95),
            "run_count": len(latencies),
            "question_pass_count": sum(question["passed"] for question in questions),
            "question_count": len(questions),
            "question_pass_rate": (
                sum(question["passed"] for question in questions) / len(questions) if questions else None
            ),
        }

    output = {
        "experiment_id": "TECH-OCR-024-R01",
        "created_on": "2026-09-28",
        "manifest": str(args.manifest.resolve()),
        "question_set": str(args.questions.resolve()),
        "source_commit": manifest["source_commit"],
        "cloud_upload_allowed": manifest["cloud_upload_allowed"],
        "rapidocr_version": importlib.metadata.version("rapidocr"),
        "rapidocr_init_ms": rapid_init_ms,
        "tesseract_version": tesseract_version,
        "tesseract_language": "chi_sim+eng",
        "tesseract_psm": 3,
        "repeats": args.repeats,
        "samples": sample_results,
        "text_layer_control": text_layer_control,
        "aggregate": aggregate,
        "limitations": [
            "No complete human transcript; CER and WER are intentionally not reported.",
            "Question checks cover only visually verified strings and same-line relations.",
            "Neither tested engine returns semantic table, formula, or seal-region structure.",
            "Repository licensing does not prove all upstream dataset image rights for redistribution.",
        ],
    }
    (output_root / "result.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"experiment_id": output["experiment_id"], "output": str(output_root)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
