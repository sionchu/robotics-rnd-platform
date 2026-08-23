# Windows Desktop: GPU and Digital Twin Lab

Observed on 2026-08-24:

| Capability | Finding |
|---|---|
| OS | Windows 11 Pro, build 26200 |
| CPU | Intel Core i5-13600KF, 14 cores / 20 logical processors |
| RAM | 31.85 GiB |
| GPU | NVIDIA GeForce RTX 4070 Ti |
| VRAM | 12,282 MiB reported by `nvidia-smi` |
| Driver / driver CUDA ceiling | 591.86 / CUDA 13.1 |
| Git / GitHub CLI | 2.48.1 / 2.96.0, authenticated over HTTPS |
| VS Code | 1.133.0 |
| Visual Studio | Build Tools 2022 17.14.36 |
| Python | global 3.11.9; project `.venv` 3.12.10 |
| CMake / Ninja | CMake 4.1.1 / Ninja 1.13.2 |
| Docker / Blender | absent before bootstrap |
| OpenUSD | `usd-core` 26.8 in project `.venv`; `usdview`/`usdcat` absent from PATH |
| Isaac Sim | `6.0.1-rc.7+release.42383.32955d8d.gl` at `C:/isaacsim`; capability-gated |
| Storage | C: 1.91 TB total; D: 3.73 TB total |

The preferred native clone is `C:/dev/robotics-rnd-platform`. Large personal
research data defaults to `D:/robotics-data` and stays outside Git.

Run `scripts/windows/doctor_windows.ps1` for a current report. Preview baseline
tool installation with `scripts/windows/bootstrap_windows.ps1`; optional tools
such as CUDA Toolkit, Blender, OpenUSD, Docker, and Isaac Sim are reported but
never installed silently.

The Windows driver exposes CUDA to installed runtimes, while a native CUDA
Toolkit (`nvcc`) is a separate optional dependency. The project `.venv` contains
PyTorch `2.12.1+cu130`; the bounded smoke operation reached CUDA successfully.
Isaac capability is tested independently.
