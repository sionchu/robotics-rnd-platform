#!/usr/bin/env python3
"""Read-only workstation capability report."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from ctypes.util import find_library
from pathlib import Path
from typing import Any


def run(command: list[str], timeout: float = 5.0) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if executable is None:
        return {"status": "missing", "detail": f"{command[0]} not found"}
    try:
        result = subprocess.run(
            [executable, *command[1:]],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "error", "detail": str(exc)}
    output = (result.stdout or result.stderr).strip()
    return {
        "status": "available" if result.returncode == 0 else "error",
        "returncode": result.returncode,
        "detail": output,
    }


def first_line(result: dict[str, Any]) -> dict[str, Any]:
    detail = str(result.get("detail", ""))
    result["detail"] = detail.splitlines()[0] if detail else ""
    return result


def os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    path = Path("/etc/os-release")
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip('"')
    return values


def memory() -> dict[str, Any]:
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        pages = os.sysconf("SC_PHYS_PAGES")
        return {"total_gib": round(page_size * pages / (1024**3), 2)}
    except (OSError, ValueError):
        return {"status": "unknown"}


def package_status(name: str) -> str:
    return "available" if importlib.util.find_spec(name) is not None else "missing"


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def nvidia_hardware(
    proc_gpu_root: Path = Path("/proc/driver/nvidia/gpus"),
    pci_root: Path = Path("/sys/bus/pci/devices"),
    *,
    driver_override: str | None = None,
) -> dict[str, Any]:
    """Report NVIDIA display devices without exposing UUIDs or serial-like values."""

    devices: list[dict[str, str]] = []
    if proc_gpu_root.is_dir():
        for information in sorted(proc_gpu_root.glob("*/information")):
            fields: dict[str, str] = {}
            text = _read_text(information) or ""
            for line in text.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    fields[key.strip()] = value.strip()
            bus = fields.get("Bus Location", information.parent.name)
            sys_device = pci_root / bus
            driver_link = sys_device / "driver"
            driver = driver_override or (driver_link.resolve().name if driver_link.exists() else "unbound")
            devices.append(
                {
                    "model": fields.get("Model", "NVIDIA GPU"),
                    "pci_address": bus,
                    "kernel_driver": driver,
                    "runtime_power": _read_text(sys_device / "power/runtime_status") or "unknown",
                }
            )
    elif pci_root.is_dir():
        for device in sorted(pci_root.iterdir()):
            vendor = _read_text(device / "vendor")
            device_class = _read_text(device / "class")
            if vendor != "0x10de" or not (device_class or "").startswith("0x03"):
                continue
            driver_link = device / "driver"
            driver = driver_override or (driver_link.resolve().name if driver_link.exists() else "unbound")
            devices.append(
                {
                    "model": "NVIDIA GPU",
                    "pci_address": device.name,
                    "kernel_driver": driver,
                    "runtime_power": _read_text(device / "power/runtime_status") or "unknown",
                }
            )
    return {
        "status": "detected" if devices else "missing",
        "devices": devices,
    }


def nvidia_driver_status(hardware: dict[str, Any], dev_root: Path = Path("/dev")) -> dict[str, Any]:
    devices = hardware.get("devices", [])
    bound = bool(devices) and all(device.get("kernel_driver") == "nvidia" for device in devices)
    control_node = (dev_root / "nvidiactl").exists()
    gpu_nodes = sorted(path.name for path in dev_root.glob("nvidia[0-9]*"))
    usable = bound and control_node and bool(gpu_nodes)
    if usable:
        detail = "NVIDIA kernel binding and character devices are available"
    elif bound:
        detail = "NVIDIA kernel binding is present but required character devices are unavailable"
    elif devices:
        detail = "NVIDIA display hardware is present but is not bound to the nvidia kernel driver"
    else:
        detail = "No NVIDIA display hardware was detected"
    return {
        "status": "usable" if usable else "unusable",
        "kernel_bound": bound,
        "control_node": control_node,
        "gpu_nodes": gpu_nodes,
        "detail": detail,
    }


def shared_library_status(name: str) -> dict[str, str]:
    library = find_library(name)
    return {
        "status": "visible" if library else "missing",
        "detail": library or f"{name} library not found",
    }


def ros_status(prefixes: list[str]) -> dict[str, Any]:
    command = first_line(run(["ros2", "--help"]))
    sourced: dict[str, Any] | None = None
    if command.get("status") != "available" and prefixes:
        setup = Path(prefixes[-1]) / "setup.bash"
        if setup.exists():
            sourced = first_line(run(["bash", "-c", f"source {setup} && ros2 --help"]))
    return {"command": command, "sourced_command": sourced, "prefixes": prefixes}


def report() -> dict[str, Any]:
    identity_name = run(["git", "config", "--get", "user.name"])
    identity_email = run(["git", "config", "--get", "user.email"])
    ros_prefixes = sorted(str(path) for path in Path("/opt/ros").glob("*") if path.is_dir())
    hardware = nvidia_hardware()
    return {
        "os": os_release(),
        "architecture": platform.machine(),
        "cpu": platform.processor() or "unknown",
        "memory": memory(),
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "packages": {
                name: package_status(name) for name in ("numpy", "pytest", "ruff", "mypy", "cv2", "torch")
            },
        },
        "git": first_line(run(["git", "--version"])),
        "git_identity": {
            "name": identity_name.get("detail", "") if identity_name.get("returncode") == 0 else "unset",
            "email": identity_email.get("detail", "") if identity_email.get("returncode") == 0 else "unset",
        },
        "compiler": first_line(run(["g++", "--version"])),
        "cmake": first_line(run(["cmake", "--version"])),
        "ninja": first_line(run(["ninja", "--version"])),
        "nvidia_gpu": hardware,
        "nvidia_driver": nvidia_driver_status(hardware),
        "nvidia_smi": run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"]
        ),
        "cuda_runtime": shared_library_status("cuda"),
        "cuda_toolkit": run(["nvcc", "--version"]),
        "ros2": ros_status(ros_prefixes),
        "docker": first_line(run(["docker", "--version"])),
        "github_cli": first_line(run(["gh", "--version"])),
    }


def main() -> int:
    print(json.dumps(report(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
