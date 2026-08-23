#!/usr/bin/env bash
set -euo pipefail

MODE="dry-run"
PROJECT_ROOT="${ROBOTICS_RND_ROOT:-$HOME/robotics/robotics-rnd-platform}"
WITH_VISION=0

usage() {
  echo "Usage: $0 [--dry-run|--install|--user-only] [--with-vision]"
  echo "Default: preview baseline packages and repository-local Python setup."
  echo "--user-only uses existing Python/compiler/CMake and installs Ninja in .venv."
}

for argument in "$@"; do
  case "$argument" in
    --dry-run) MODE="dry-run" ;;
    --install) MODE="install" ;;
    --user-only) MODE="user-only" ;;
    --with-vision) WITH_VISION=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $argument" >&2; usage >&2; exit 2 ;;
  esac
done

if ! grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null; then
  echo "This bootstrap is for Ubuntu under WSL2." >&2
  exit 1
fi

if [[ ! -f /etc/os-release ]] || ! grep -q '^ID=ubuntu$' /etc/os-release; then
  echo "This bootstrap supports Ubuntu under WSL2 only." >&2
  exit 1
fi

APT_PACKAGES=(build-essential cmake git ninja-build python3.12 python3.12-dev python3.12-venv)

echo "Mode: $MODE"
echo "Repository: $PROJECT_ROOT"
echo "Baseline apt packages: ${APT_PACKAGES[*]}"
echo "The Windows NVIDIA driver supplies WSL GPU support."
echo "No Linux display driver, CUDA meta-package, Docker, ROS, Isaac, or vendor SDK is installed."

if [[ "$MODE" == "dry-run" ]]; then
  echo "Preview only. Re-run with --install after reviewing the commands above."
  exit 0
fi

if [[ ! -d "$PROJECT_ROOT/.git" ]]; then
  echo "Clone the canonical private repository into $PROJECT_ROOT before installation." >&2
  exit 1
fi

if [[ "$MODE" == "install" ]]; then
  sudo apt-get update
  sudo apt-get install --yes "${APT_PACKAGES[@]}"
else
  for command_name in python3.12 git cmake g++; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
      echo "--user-only requires existing command: $command_name" >&2
      exit 1
    fi
  done
fi

python3.12 -m venv "$PROJECT_ROOT/.venv"
"$PROJECT_ROOT/.venv/bin/python" -m pip install --upgrade pip
if [[ "$MODE" == "user-only" ]]; then
  "$PROJECT_ROOT/.venv/bin/python" -m pip install ninja
fi
if [[ "$WITH_VISION" -eq 1 ]]; then
  "$PROJECT_ROOT/.venv/bin/python" -m pip install -e "$PROJECT_ROOT[dev,vision]"
else
  "$PROJECT_ROOT/.venv/bin/python" -m pip install -e "$PROJECT_ROOT[dev]"
fi
"$PROJECT_ROOT/.venv/bin/pre-commit" install
echo "Bootstrap complete. Activate with: source $PROJECT_ROOT/.venv/bin/activate"
