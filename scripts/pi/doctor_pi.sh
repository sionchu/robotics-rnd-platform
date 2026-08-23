#!/usr/bin/env bash
set -euo pipefail

pi_host="${ROBOTICS_RND_PI_HOST:-pi-rnd}"
output_file=""

while (($#)); do
  case "$1" in
    --host) pi_host="$2"; shift 2 ;;
    --output) output_file="$2"; shift 2 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if [[ ! "$pi_host" =~ ^[A-Za-z0-9._-]+$ ]]; then
  printf 'host must be a configured SSH alias or simple hostname\n' >&2
  exit 2
fi

doctor_output="$(mktemp)"
trap 'rm -f -- "$doctor_output"' EXIT

ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 "$pi_host" python3 - >"$doctor_output" <<'PY'
import importlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def command(arguments):
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "missing", "detail": str(exc)}
    text = (result.stdout or result.stderr).strip()
    return {"status": "available" if result.returncode == 0 else "error", "detail": text}


def module_version(name):
    try:
        module = importlib.import_module(name)
    except ImportError:
        return None
    return str(getattr(module, "__version__", "unknown"))


os_release = {}
for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        os_release[key] = value.strip('"')

board_path = Path("/proc/device-tree/model")
board_model = board_path.read_bytes().replace(b"\0", b"").decode("utf-8") if board_path.exists() else None
document = {
    "schema": "robotics-rnd-pi-hardware-manifest-v1",
    "device_role": "edge-vision-node",
    "board_model": board_model,
    "architecture": platform.machine(),
    "os": os_release.get("PRETTY_NAME"),
    "kernel": platform.release(),
    "python": platform.python_version(),
    "picamera2": module_version("picamera2"),
    "opencv": module_version("cv2"),
    "rpicam_apps": command(["rpicam-hello", "--version"]),
    "camera_inventory": command(["rpicam-hello", "--list-cameras"]),
    "timestamp": datetime.now(UTC).isoformat(),
    "hardware_validated": True,
    "privacy": "serials, MAC addresses, hostnames, addresses, and credentials intentionally omitted",
}
print(json.dumps(document, indent=2, sort_keys=True))
PY

if [[ -n "$output_file" ]]; then
  install -D -m 0600 "$doctor_output" "$output_file"
  printf 'sanitized manifest written to %s\n' "$output_file"
else
  cat "$doctor_output"
fi
