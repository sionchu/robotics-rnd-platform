#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="dry-run"
WITH_VISION=0

usage() {
  echo "Usage: $0 [--dry-run|--install] [--with-vision]"
  echo "Default: preview baseline packages and local Python setup without changing the system."
}

for argument in "$@"; do
  case "$argument" in
    --dry-run) MODE="dry-run" ;;
    --install) MODE="install" ;;
    --with-vision) WITH_VISION=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $argument" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! -f /etc/os-release ]] || ! grep -q '^ID=ubuntu$' /etc/os-release; then
  echo "This bootstrap supports Ubuntu only." >&2
  exit 1
fi

APT_PACKAGES=(build-essential cmake git ninja-build python3.12 python3.12-dev python3.12-venv)

echo "Mode: $MODE"
echo "Repository: $PROJECT_ROOT"
echo "Baseline apt packages: ${APT_PACKAGES[*]}"
echo "Python environment: .venv with editable development dependencies"
if [[ "$WITH_VISION" -eq 1 ]]; then
  echo "Optional Python group: vision (OpenCV headless)"
fi
echo "ROS 2, CUDA, Isaac, Docker, and vendor SDKs are not installed by this script."

if [[ "$MODE" == "dry-run" ]]; then
  echo "Preview only. Re-run with --install after reviewing the commands above."
  exit 0
fi

sudo apt-get update
sudo apt-get install --yes "${APT_PACKAGES[@]}"
python3.12 -m venv "$PROJECT_ROOT/.venv"
"$PROJECT_ROOT/.venv/bin/python" -m pip install --upgrade pip
if [[ "$WITH_VISION" -eq 1 ]]; then
  "$PROJECT_ROOT/.venv/bin/python" -m pip install -e "$PROJECT_ROOT[dev,vision]"
else
  "$PROJECT_ROOT/.venv/bin/python" -m pip install -e "$PROJECT_ROOT[dev]"
fi
"$PROJECT_ROOT/.venv/bin/pre-commit" install
echo "Bootstrap complete. Activate with: source $PROJECT_ROOT/.venv/bin/activate"
