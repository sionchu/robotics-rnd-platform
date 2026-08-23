# Ubuntu Workstation Baseline

Observed read-only on 2026-08-23:

| Capability | Finding |
|---|---|
| OS | Ubuntu 24.04 LTS (Noble) |
| Architecture | x86_64 |
| CPU | AMD Ryzen AI 7 350, 8 cores / 16 logical CPUs |
| RAM | approximately 30 GiB, no swap configured |
| Python | CPython 3.12.3 |
| Git | 2.43.0 |
| C++ compiler | g++ 13.2.0 |
| CMake / Ninja | 3.28.3 / 1.11.1 |
| NVIDIA | `nvidia-smi` cannot communicate with a driver |
| CUDA | `nvcc` not installed |
| ROS 2 | Jazzy prefix installed; CLI works after sourcing `/opt/ros/jazzy/setup.bash` |
| Docker | command not installed |
| GitHub CLI | installed and authenticated |

Run `python scripts/doctor.py` for a current JSON report. It does not modify the
host. Run `./scripts/bootstrap_ubuntu.sh --dry-run` to preview baseline packages.

## Baseline setup

Use the system Python 3.12 interpreter in a repository-local virtual environment.
The editable `dev` group supplies pytest, Ruff, mypy, and pre-commit. OpenCV is a
separate `vision` group. ROS binary packages, CUDA/TensorRT, Isaac, and vendor
SDKs need separate version-specific procedures and are intentionally excluded
from bootstrap.

## ROS 2 note

Jazzy is present but intentionally not sourced into every shell. Use the official
setup script in a dedicated ROS shell and keep ROS workspaces/environments
separate from the generic Python environment. ROS binary packages depend on the
distribution's Python ABI; verify interpreter alignment.

## GPU note

Do not install CUDA or Isaac merely to satisfy a roadmap checkbox. First make the
NVIDIA driver functional, identify the GPU and support matrix, then select a
versioned CUDA/TensorRT/Isaac path. Preserve CPU reference results.
