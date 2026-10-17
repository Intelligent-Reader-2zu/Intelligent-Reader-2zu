from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/ocr-ppstructure-v3"
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(OUT / "model-cache"))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

import torch  # noqa: E402,F401
import paddle  # noqa: E402
from paddleocr import PPStructureV3  # noqa: E402


def json_safe(value):
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def result_json(value):
    raw = getattr(value, "json", None)
    raw = raw() if callable(raw) else raw
    if isinstance(raw, str):
        return json.loads(raw)
    if raw is not None:
        return json_safe(raw)
    return {"repr": str(value)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample",
        choices=("SELF-002-page-1", "SELF-004-page-1", "SELF-004-page-1-1000px"),
    )
    args = parser.parse_args()
    diagnostic_small = args.sample == "SELF-004-page-1-1000px"
    revision = "R03" if diagnostic_small else "R02"
    experiment_id = f"TECH-OCR-020-{revision}"
    OUT.mkdir(parents=True, exist_ok=True)
    if diagnostic_small:
        samples = {
            "SELF-004-page-1-1000px": OUT / "inputs/SELF-004-page-1-1000px.png",
        }
    else:
        samples = {
            "SELF-002-page-1": ROOT / "results/text-structure/rendered/SELF-002-1.png",
            "SELF-004-page-1": ROOT / "results/ocr-tesseract-matrix/dpi144-psm3-none/page-1.png",
        }
    pipeline_settings = {
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
        "use_seal_recognition": False,
        "use_table_recognition": True,
        "use_formula_recognition": False,
        "use_chart_recognition": False,
        "use_region_detection": False,
        "lang": "ch",
    }
    runtime_settings = {
        "device": "cpu",
        "enable_mkldnn": False,
    }
    predict_settings = {
        **pipeline_settings,
        "use_table_orientation_classify": False,
    }

    started = time.perf_counter()
    try:
        engine = PPStructureV3(**pipeline_settings, **runtime_settings)
    except Exception as exc:
        result = {
            "experiment_id": experiment_id,
            "status": "initialization_failed",
            "paddleocr_version": importlib.metadata.version("paddleocr"),
            "paddle_version": paddle.__version__,
            "python_version": os.sys.version.split()[0],
            "settings": {**pipeline_settings, **runtime_settings},
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        (OUT / f"result-{revision}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps({"experiment_id": result["experiment_id"], "status": result["status"]}, ensure_ascii=False))
        return
    init_ms = (time.perf_counter() - started) * 1000

    samples_out = []
    for sample_id, image_path in samples.items():
        page_result_path = OUT / f"{sample_id}-{revision}.json"
        if args.sample is not None and sample_id != args.sample:
            if page_result_path.exists():
                samples_out.append(json.loads(page_result_path.read_text(encoding="utf-8")))
            continue
        started = time.perf_counter()
        try:
            outputs = [result_json(item) for item in engine.predict(str(image_path), **predict_settings)]
            sample = {
                "sample_id": sample_id,
                "status": "succeeded",
                "image_path": str(image_path),
                "input_sha256": sha256(image_path),
                "elapsed_ms": (time.perf_counter() - started) * 1000,
                "outputs": outputs,
            }
        except Exception as exc:
            sample = {
                "sample_id": sample_id,
                "status": "failed",
                "image_path": str(image_path),
                "input_sha256": sha256(image_path),
                "elapsed_ms": (time.perf_counter() - started) * 1000,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        samples_out.append(sample)
        page_result_path.write_text(
            json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    result = {
        "experiment_id": experiment_id,
        "status": "succeeded" if all(sample["status"] == "succeeded" for sample in samples_out) else "partial_or_failed",
        "paddleocr_version": importlib.metadata.version("paddleocr"),
        "paddle_version": paddle.__version__,
        "python_version": os.sys.version.split()[0],
        "settings": {**predict_settings, **runtime_settings},
        "model_init_ms": init_ms,
        "samples": samples_out,
        "boundary": "Two project-authored pages; smoke test without manually annotated cell/layout ground truth.",
    }
    (OUT / f"result-{revision}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"experiment_id": result["experiment_id"], "status": result["status"], "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
