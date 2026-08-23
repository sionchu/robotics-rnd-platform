#!/usr/bin/env bash
set -uo pipefail

PROJECT_ROOT="${ROBOTICS_RND_ROOT:-$HOME/robotics/robotics-rnd-platform}"
DATA_ROOT="${ROBOTICS_DATA_ROOT:-$HOME/robotics-data}"
PYTHON_BIN="python3"
NINJA_BIN="ninja"
if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
fi
if [[ -x "$PROJECT_ROOT/.venv/bin/ninja" ]]; then
  NINJA_BIN="$PROJECT_ROOT/.venv/bin/ninja"
fi

finding() {
  printf '%-12s %-24s %s\n' "$1" "$2" "$3"
}

command_finding() {
  local label="$1"
  local command_name="$2"
  shift 2
  if command -v "$command_name" >/dev/null 2>&1; then
    local detail
    detail="$("$@" 2>&1 | head -n 1)"
    finding PASS "$label" "$detail"
  else
    finding MISSING "$label" "$command_name not found"
  fi
}

if grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null; then
  finding PASS WSL "WSL2 kernel detected"
else
  finding UNSUPPORTED WSL "not running under WSL"
fi

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  finding PASS OS "${PRETTY_NAME:-unknown}"
else
  finding UNKNOWN OS "/etc/os-release unavailable"
fi

command_finding Python "$PYTHON_BIN" "$PYTHON_BIN" --version
command_finding GCC gcc gcc --version
command_finding G++ g++ g++ --version
command_finding CMake cmake cmake --version
command_finding Ninja "$NINJA_BIN" "$NINJA_BIN" --version
command_finding Git git git --version
command_finding Docker docker docker --version

if command -v nvidia-smi >/dev/null 2>&1; then
  gpu="$(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | head -n 1)"
  if [[ -n "$gpu" ]]; then
    finding PASS NVIDIA "$gpu"
  else
    finding WARN NVIDIA "nvidia-smi returned no GPU"
  fi
else
  finding MISSING NVIDIA "nvidia-smi not found"
fi

if "$PYTHON_BIN" -c 'import torch' >/dev/null 2>&1; then
  torch_status="$("$PYTHON_BIN" -c 'import torch; print(f"torch={torch.__version__} cuda={torch.cuda.is_available()} runtime={torch.version.cuda}")')"
  finding PASS PyTorch "$torch_status"
else
  finding MISSING PyTorch "torch not installed"
fi

if [[ -d "$PROJECT_ROOT/.git" ]]; then
  branch="$(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null)"
  commit="$(git -C "$PROJECT_ROOT" rev-parse --short=12 HEAD 2>/dev/null)"
  if [[ -n "$(git -C "$PROJECT_ROOT" status --short 2>/dev/null)" ]]; then
    cleanliness="dirty"
  else
    cleanliness="clean"
  fi
  finding PASS Repository "branch=$branch commit=$commit $cleanliness"
else
  finding MISSING Repository "expected Linux-filesystem clone is absent"
fi

if [[ -d "$DATA_ROOT" ]]; then
  finding PASS DataRoot "configured directory exists"
else
  finding WARN DataRoot "create outside Git when data work begins"
fi

finding WARN CUDA-Driver "use the Windows NVIDIA driver; never install a Linux display driver in WSL"
