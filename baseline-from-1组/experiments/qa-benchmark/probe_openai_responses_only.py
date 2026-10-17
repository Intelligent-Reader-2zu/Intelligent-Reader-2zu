"""Send exactly one minimal POST request through the OpenAI Responses API."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from openai import OpenAI


OUT = Path(__file__).resolve().parent / "results"


def main() -> None:
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")
    model = os.environ.get("OPENAI_MODEL", "gpt-5.5")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.ipc.wiki/v1")
    timeout = float(os.environ.get("OPENAI_TIMEOUT_SECONDS", "60"))
    if not key:
        raise SystemExit("OPENAI_API_KEY is required")
    client = OpenAI(api_key=key, base_url=base_url, timeout=timeout, max_retries=0)
    started = time.perf_counter()
    result = {
        "experiment_id": "TECH-QA-023-R01",
        "endpoint": base_url.rstrip("/") + "/responses",
        "model": model,
        "timeout_seconds": timeout,
        "request_sent": True,
    }
    try:
        response = client.responses.create(
            model=model,
            instructions="Return the JSON object {\"ok\":true} and nothing else.",
            input="Return only the requested JSON object.",
            max_output_tokens=80,
            store=False,
        )
        result.update({"ok": True, "output": response.output_text, "response_id": getattr(response, "id", None)})
    except Exception as exc:
        result.update({"ok": False, "error_type": type(exc).__name__, "error": str(exc)})
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "TECH-QA-023-R01.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    safe = {k: v for k, v in result.items() if k != "output"}
    (OUT / "TECH-QA-023-R01.md").write_text("# TECH-QA-023-R01 Responses-only probe\n\n" + json.dumps(safe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(safe, ensure_ascii=False))


if __name__ == "__main__":
    main()
