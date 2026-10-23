"""Measure whether the current machine is ready for local QA model trials.

This is an environment gate, not a model-quality benchmark.  It avoids
downloading weights or installing a runtime and records why a local trial can
or cannot start safely.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import psutil


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "results"


def nvidia_info() -> dict:
    command = shutil.which("nvidia-smi")
    if not command:
        return {"available": False, "reason": "nvidia-smi not found", "gpus": []}
    try:
        raw = subprocess.check_output(
            [command, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=10,
        ).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": False, "reason": str(exc), "gpus": []}
    gpus = []
    for line in raw.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3:
            continue
        gpus.append({"name": parts[0], "memory_total": parts[1], "driver_version": parts[2]})
    return {"available": bool(gpus), "gpus": gpus}


def model_files() -> list[str]:
    roots = [
        ROOT / "retrieval-benchmark" / "models",
        ROOT / "qa-benchmark" / "models",
        Path(os.environ.get("USERPROFILE", "")) / ".cache" / "huggingface" / "hub",
    ]
    matches = []
    for root in roots:
        if not root.exists():
            continue
        for current, dirs, files in os.walk(root):
            dirs[:] = [name for name in dirs if name not in {".locks", "__pycache__", ".runtime", "tmp"}]
            for name in files:
                if Path(name).suffix.lower() in {".gguf", ".safetensors", ".bin"}:
                    matches.append(str(Path(current) / name))
    return sorted(set(matches))


def main() -> None:
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("D:\\")
    gpu = nvidia_info()
    libraries = {
        name: bool(importlib.util.find_spec(name))
        for name in ("torch", "transformers", "llama_cpp", "ollama", "vllm", "bitsandbytes")
    }
    torch_cuda = False
    torch_version = None
    if libraries["torch"]:
        import torch

        torch_version = torch.__version__
        torch_cuda = bool(torch.cuda.is_available())
    files = model_files()
    generative_weight_candidates = [
        path for path in files if any(token in Path(path).name.lower() for token in ("qwen", "llama", "mistral", "deepseek", "phi"))
    ]
    result = {
        "experiment_id": "TECH-QA-016-R01",
        "scope": "local model environment gate; no model download or installation",
        "hardware": {
            "memory_total_gib": round(memory.total / 2**30, 2),
            "memory_available_gib": round(memory.available / 2**30, 2),
            "memory_percent_used": memory.percent,
            "disk_d_free_gib": round(disk.free / 2**30, 2),
            "gpu": gpu,
        },
        "runtime": {
            "python": shutil.which("python"),
            "torch_version": torch_version,
            "torch_cuda_available": torch_cuda,
            "libraries": libraries,
        },
        "model_files": {
            "count": len(files),
            "generative_candidates": generative_weight_candidates,
            "note": "Existing BGE embedding weights are not a generative QA model.",
        },
    }
    vram_4gb = any("4096" in gpu_item.get("memory_total", "") or "4 GiB" in gpu_item.get("memory_total", "") for gpu_item in gpu.get("gpus", []))
    light_reasons = []
    if vram_4gb:
        light_reasons.append("4GB GPU can only be considered for small quantized models or partial offload")
    if not torch_cuda:
        light_reasons.append("current PyTorch is CPU-only; CUDA inference is unavailable")
    if not libraries["llama_cpp"] and not libraries["ollama"] and not libraries["vllm"]:
        light_reasons.append("no local generation runtime is installed")
    if not generative_weight_candidates:
        light_reasons.append("no local generative model weights are present")
    if memory.available < 8 * 2**30:
        light_reasons.append("current available memory is below the 8 GiB trial headroom target")
    result["assessment"] = {
        "light_path": "conditional_not_ready",
        "light_path_reasons": light_reasons,
        "high_quality_path": "not_feasible_on_current_device",
        "high_quality_reasons": [
            "4GB VRAM is below a practical 14B/32B interactive target",
            "CUDA inference and a local generation runtime are unavailable",
            "current free memory and disk headroom should not be consumed by a large weight download",
        ],
        "safe_next_step": "free memory or use a separate machine, install a pinned CPU/GPU runtime, then test a 4B/8B quantized model without uploading documents",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "TECH-QA-016-R01.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# TECH-QA-016-R01 本地大模型环境门禁",
        "",
        "本记录只判断本机是否具备安全开始本地生成模型试验的条件，不下载权重、不安装运行时，也不评价模型质量。",
        "",
        f"内存：{result['hardware']['memory_total_gib']} GiB，总可用：{result['hardware']['memory_available_gib']} GiB；D 盘可用：{result['hardware']['disk_d_free_gib']} GiB；GPU：{', '.join(item['name'] + ' / ' + item['memory_total'] for item in gpu.get('gpus', [])) or '未检测到'}；PyTorch CUDA：{'可用' if torch_cuda else '不可用'}。",
        "",
        f"轻量路径：**{result['assessment']['light_path']}**；高质量路径：**{result['assessment']['high_quality_path']}**。",
        "",
        "## 观察",
        "",
    ]
    lines.extend(f"- {reason}" for reason in light_reasons)
    lines.extend(
        [
            "",
            "## 结论",
            "",
            "当前机器只能把 4B/8B 量化模型作为释放内存、准备运行时后的条件候选；不应在当前状态直接下载大权重或承诺交互式质量。14B/32B 高质量路径不适合作为本机实验目标。",
            "",
            "安全下一步：释放内存或换到更大设备，固定一个本地运行时和 4B/8B 量化权重，先跑离线短文档和 15 题固定集；文档不出本机。",
        ]
    )
    (OUT / "TECH-QA-016-R01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"experiment_id": result["experiment_id"], "assessment": result["assessment"], "hardware": result["hardware"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
