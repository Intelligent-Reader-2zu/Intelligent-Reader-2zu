from __future__ import annotations

import importlib.metadata
import json
import os
import time
from collections import Counter
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/ocr-ppstructure"
os.environ.setdefault("PADDLE_OCR_BASE_DIR", str(OUT / "model-cache"))

import paddle  # noqa: E402
from paddleocr import PPStructure  # noqa: E402


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


def simplify_region(region: dict) -> dict:
    simplified = {key: json_safe(value) for key, value in region.items() if key != "img"}
    image = region.get("img")
    if image is not None and hasattr(image, "shape"):
        simplified["region_image_shape"] = list(image.shape)
    return simplified


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    samples = {
        "SELF-004-page-1": ROOT / "results/ocr-tesseract-matrix/dpi144-psm3-none/page-1.png",
        "SELF-004-page-2": ROOT / "results/ocr-tesseract-matrix/dpi144-psm3-none/page-2.png",
        "SELF-002-page-1": ROOT / "results/text-structure/rendered/SELF-002-1.png",
        "SELF-002-page-2": ROOT / "results/text-structure/rendered/SELF-002-2.png",
    }

    full_pipeline_error = None
    try:
        PPStructure(show_log=False, lang="ch", layout=True, table=True, formula=False, ocr=True)
    except Exception as exc:
        full_pipeline_error = {"error_type": type(exc).__name__, "error": str(exc)}

    started = time.perf_counter()
    engine = PPStructure(show_log=False, lang="ch", layout=True, table=False, formula=False, ocr=True)
    init_ms = (time.perf_counter() - started) * 1000
    outputs = []
    for sample_id, image_path in samples.items():
        image = cv2.imread(str(image_path))
        if image is None:
            outputs.append({"sample_id": sample_id, "status": "failed", "error": f"cannot read {image_path}"})
            continue
        started = time.perf_counter()
        try:
            raw = engine(image)
            elapsed_ms = (time.perf_counter() - started) * 1000
            regions = [simplify_region(region) for region in raw]
            counts = Counter(str(region.get("type", "unknown")) for region in regions)
            output = {
                "sample_id": sample_id,
                "status": "succeeded",
                "image_path": str(image_path),
                "image_shape": list(image.shape),
                "elapsed_ms": elapsed_ms,
                "region_type_counts": dict(counts),
                "regions": regions,
            }
        except Exception as exc:
            output = {
                "sample_id": sample_id,
                "status": "failed",
                "image_path": str(image_path),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        outputs.append(output)
        (OUT / f"{sample_id}.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {
        "experiment_id": "TECH-OCR-018-R01",
        "engine": "PP-StructureV2",
        "paddleocr_version": importlib.metadata.version("paddleocr"),
        "paddle_version": paddle.__version__,
        "python_version": os.sys.version.split()[0],
        "configuration": {"layout": True, "table": False, "formula": False, "ocr": True},
        "full_pipeline_init_error": full_pipeline_error,
        "model_init_ms": init_ms,
        "samples": outputs,
        "boundary": "Four project-authored page images; smoke test only, without manually annotated layout/table ground truth.",
    }
    (OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"experiment_id": result["experiment_id"], "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
