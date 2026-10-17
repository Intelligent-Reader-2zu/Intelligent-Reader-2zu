"""Probe an OpenAI-compatible relay with one minimal request per wire API.

This sends no project documents. It is for distinguishing relay endpoint
compatibility from model-quality failures. It never prints the API key.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from openai import OpenAI


OUT = Path(__file__).resolve().parent / "results"


def main() -> None:
    key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.ipc.wiki/v1")
    if not key or not model:
        raise SystemExit("OPENAI_API_KEY and OPENAI_MODEL are required")
    client = OpenAI(api_key=key, base_url=base_url, timeout=10, max_retries=0)
    result = {"experiment_id": "TECH-QA-018-R01", "base_url": base_url, "model": model, "probes": []}
    try:
        start = time.perf_counter()
        models = client.models.list()
        result["models_probe"] = {"ok": True, "elapsed_ms": round((time.perf_counter() - start) * 1000, 3), "data_count": len(models.data)}
    except Exception as exc:
        result["models_probe"] = {"ok": False, "error_type": type(exc).__name__, "error": str(exc)}
    for wire_api in ("responses", "chat_completions"):
        probe = {"wire_api": wire_api}
        start = time.perf_counter()
        try:
            if wire_api == "responses":
                response = client.responses.create(
                    model=model,
                    instructions="Return JSON only.",
                    input="Evidence: BM25 uses term frequency, inverse document frequency, and document length. Question: What does BM25 use? Answer briefly.",
                    max_output_tokens=80,
                    text={"format": {"type": "json_object"}},
                )
                probe["text"] = response.output_text
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Return the JSON object {\"ok\":true}."}],
                    max_tokens=30,
                    response_format={"type": "json_object"},
                )
                probe["text"] = response.choices[0].message.content
            probe["ok"] = True
        except Exception as exc:
            probe["ok"] = False
            probe["error_type"] = type(exc).__name__
            probe["error"] = str(exc)
        probe["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 3)
        result["probes"].append(probe)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "TECH-QA-018-R01.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    safe = {
        "experiment_id": result["experiment_id"],
        "base_url": base_url,
        "model": model,
        "models_probe": result["models_probe"],
        "probes": [{k: v for k, v in probe.items() if k != "text"} for probe in result["probes"]],
    }
    (OUT / "TECH-QA-018-R01.md").write_text("# TECH-QA-018-R01 OpenAI 中转站接口探测\n\n" + json.dumps(safe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(safe, ensure_ascii=False))


if __name__ == "__main__":
    main()
