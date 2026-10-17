# TECH-QA-018-R01 OpenAI 中转站接口探测

{
  "experiment_id": "TECH-QA-018-R01",
  "base_url": "https://api.ipc.wiki/v1",
  "model": "gpt-5.5",
  "models_probe": {
    "ok": false,
    "error_type": "APIConnectionError",
    "error": "Connection error."
  },
  "probes": [
    {
      "wire_api": "responses",
      "ok": false,
      "error_type": "APIConnectionError",
      "error": "Connection error.",
      "elapsed_ms": 52.037
    },
    {
      "wire_api": "chat_completions",
      "ok": false,
      "error_type": "APIConnectionError",
      "error": "Connection error.",
      "elapsed_ms": 2.002
    }
  ]
}
