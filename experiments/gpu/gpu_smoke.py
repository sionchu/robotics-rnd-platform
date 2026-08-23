#!/usr/bin/env python3
"""Run a tiny, explicit PyTorch CUDA operation and write a comparable report."""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_executable(name: str) -> str | None:
    executable = shutil.which(name)
    if executable is not None:
        return executable
    if platform.system() == "Linux" and name == "nvidia-smi":
        wsl_nvidia_smi = Path("/usr/lib/wsl/lib/nvidia-smi")
        if wsl_nvidia_smi.is_file():
            return str(wsl_nvidia_smi)
    return None


def run(command: list[str], timeout: float = 10.0) -> dict[str, Any]:
    executable = resolve_executable(command[0])
    if executable is None:
        return {"status": "MISSING", "detail": f"{command[0]} not found"}
    try:
        result = subprocess.run(
            [executable, *command[1:]],
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "UNKNOWN", "detail": str(exc)}
    return {
        "status": "PASS" if result.returncode == 0 else "WARN",
        "returncode": result.returncode,
        "detail": (result.stdout or result.stderr).strip(),
    }


def commit_sha() -> str:
    result = run(["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"])
    return str(result.get("detail", "unknown")) if result.get("returncode") == 0 else "unknown"


def nvidia_status() -> dict[str, Any]:
    result = run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader,nounits",
        ]
    )
    if result.get("returncode") != 0:
        return result
    line = str(result.get("detail", "")).splitlines()[0]
    parts = [part.strip() for part in line.split(",")]
    if len(parts) != 3:
        return {"status": "WARN", "detail": line}
    return {
        "status": "PASS",
        "model": parts[0],
        "vram_mib": int(parts[1]),
        "driver": parts[2],
    }


def torch_benchmark(matrix_size: int, iterations: int) -> dict[str, Any]:
    if importlib.util.find_spec("torch") is None:
        return {"status": "MISSING", "detail": "PyTorch is not installed"}

    import torch

    result: dict[str, Any] = {
        "status": "WARN",
        "torch_version": torch.__version__,
        "torch_cuda_runtime": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "matrix_size": matrix_size,
        "iterations": iterations,
    }
    if not torch.cuda.is_available():
        result["detail"] = "PyTorch cannot access CUDA"
        return result

    torch.manual_seed(20260824)
    device = torch.device("cuda:0")
    left = torch.randn((matrix_size, matrix_size), device=device, dtype=torch.float32)
    right = torch.randn((matrix_size, matrix_size), device=device, dtype=torch.float32)
    for _ in range(2):
        product = left @ right
    torch.cuda.synchronize(device)
    torch.cuda.reset_peak_memory_stats(device)

    started = time.perf_counter()
    for _ in range(iterations):
        product = left @ right
    torch.cuda.synchronize(device)
    elapsed = time.perf_counter() - started

    result.update(
        {
            "status": "PASS",
            "device_name": torch.cuda.get_device_name(device),
            "compute_capability": ".".join(str(value) for value in torch.cuda.get_device_capability(device)),
            "checksum": float(product[0, 0].item()),
            "total_elapsed_ms": round(elapsed * 1000, 4),
            "mean_elapsed_ms": round(elapsed * 1000 / iterations, 4),
            "peak_allocated_mib": round(torch.cuda.max_memory_allocated(device) / 1024**2, 3),
        }
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-size", type=int, default=512)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-cuda", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.matrix_size < 16 or args.matrix_size > 4096:
        raise SystemExit("--matrix-size must be between 16 and 4096")
    if args.iterations < 1 or args.iterations > 1000:
        raise SystemExit("--iterations must be between 1 and 1000")

    benchmark = torch_benchmark(args.matrix_size, args.iterations)
    report = {
        "experiment": "pytorch-cuda-matmul-smoke-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "commit_sha": commit_sha(),
        "machine_profile": "windows-desktop" if platform.system() == "Windows" else "wsl2-desktop",
        "os": platform.platform(),
        "python": platform.python_version(),
        "gpu": nvidia_status(),
        "parameters": {"matrix_size": args.matrix_size, "iterations": args.iterations, "dtype": "float32"},
        "result": benchmark,
        "notes": "Safe synthetic tensor operation; no dataset, model, hardware motion, or vendor SDK used.",
    }
    payload = json.dumps(report, indent=2, sort_keys=True)
    print(payload)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{payload}\n", encoding="utf-8")

    if args.require_cuda and benchmark.get("status") != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
