#!/usr/bin/env python3
"""Cross-platform, read-only repository and runtime capability report."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def resolve_executable(name: str) -> str | None:
    executable = shutil.which(name)
    if executable is not None:
        return executable
    if platform.system() == "Windows" and name == "ninja":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            package_root = Path(local_app_data) / "Microsoft/WinGet/Packages"
            matches = sorted(package_root.glob("Ninja-build.Ninja_*/ninja.exe"))
            if matches:
                return str(matches[-1])
    return None


def run(command: list[str], cwd: Path | None = None, timeout: float = 10.0) -> dict[str, Any]:
    executable = resolve_executable(command[0])
    if executable is None:
        return {"status": "MISSING", "detail": f"{command[0]} not found"}
    try:
        result = subprocess.run(
            [executable, *command[1:]],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "UNKNOWN", "detail": str(exc)}
    output = (result.stdout or result.stderr).strip()
    return {
        "status": "PASS" if result.returncode == 0 else "WARN",
        "returncode": result.returncode,
        "detail": output,
    }


def first_line(result: dict[str, Any]) -> dict[str, Any]:
    detail = str(result.get("detail", ""))
    result["detail"] = detail.splitlines()[0] if detail else ""
    return result


def repository_report(root: Path) -> dict[str, Any]:
    inside = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root)
    if inside.get("detail") != "true":
        return {"status": "MISSING", "detail": "repository metadata not found"}
    branch = first_line(run(["git", "branch", "--show-current"], cwd=root))
    commit = first_line(run(["git", "rev-parse", "--short=12", "HEAD"], cwd=root))
    status = run(["git", "status", "--short"], cwd=root)
    remote = run(["git", "remote", "get-url", "origin"], cwd=root)
    return {
        "status": "PASS",
        "branch": branch.get("detail", ""),
        "commit": commit.get("detail", ""),
        "clean": status.get("returncode") == 0 and not status.get("detail"),
        "origin_configured": remote.get("returncode") == 0,
    }


def python_packages() -> dict[str, Any]:
    packages: dict[str, Any] = {}
    for name in ("numpy", "pytest", "ruff", "mypy", "cv2", "torch", "pxr"):
        packages[name] = "PASS" if importlib.util.find_spec(name) is not None else "MISSING"
    torch_detail: dict[str, Any] = {"installed": packages["torch"] == "PASS"}
    if torch_detail["installed"]:
        import torch

        torch_detail.update(
            {
                "version": torch.__version__,
                "cuda_runtime": torch.version.cuda,
                "cuda_available": torch.cuda.is_available(),
                "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            }
        )
    return {"packages": packages, "torch": torch_detail}


def storage_report() -> dict[str, Any]:
    anchor = Path.cwd().anchor or "/"
    usage = shutil.disk_usage(anchor)
    data_root = os.environ.get("ROBOTICS_DATA_ROOT")
    return {
        "workspace_volume": {
            "total_gib": round(usage.total / 1024**3, 2),
            "free_gib": round(usage.free / 1024**3, 2),
        },
        "data_root": {
            "configured": data_root is not None,
            "exists": bool(data_root and Path(data_root).expanduser().exists()),
        },
    }


def build_report(root: Path, role: str) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "machine_role": role,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine(),
            "cpu": platform.processor() or "unknown",
        },
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            **python_packages(),
        },
        "tools": {
            "git": first_line(run(["git", "--version"])),
            "github_cli": first_line(run(["gh", "--version"])),
            "compiler": first_line(run(["g++", "--version"])),
            "cmake": first_line(run(["cmake", "--version"])),
            "ninja": first_line(run(["ninja", "--version"])),
            "docker": first_line(run(["docker", "--version"])),
            "nvidia": run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader",
                ]
            ),
            "cuda_compiler": first_line(run(["nvcc", "--version"])),
        },
        "repository": repository_report(root),
        "storage": storage_report(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", default="unknown", help="generic machine role, not a hostname")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, help="optional local JSON report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.root.expanduser().resolve(), args.role)
    payload = json.dumps(report, indent=2, sort_keys=True)
    print(payload)
    if args.output is not None:
        output = args.output.expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(f"{payload}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
