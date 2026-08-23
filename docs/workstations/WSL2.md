# Windows WSL2: Linux Build and GPU-Support Lab

The desktop has Ubuntu 24.04.3 LTS under WSL 2 with Python 3.12.3, GCC/G++ 13.3,
CMake 3.28.3, Git 2.43.0, and visible RTX 4070 Ti telemetry through the Windows
driver. The user-only bootstrap added an independent project `.venv`, Ninja
1.13.0, and PyTorch `2.12.1+cu130`. Docker remains absent.

The canonical WSL clone path is:

```text
~/robotics/robotics-rnd-platform
```

Keep it in the Linux filesystem and use its own `.venv`, build directories, and
`~/robotics-data`. Do not use the Windows clone under `/mnt/c` as the main Linux
checkout.

CUDA on WSL uses the Windows NVIDIA driver. Never install a Linux display driver
inside WSL. If a compiler toolkit is needed later, follow NVIDIA's WSL-specific
toolkit instructions and avoid driver meta-packages. Run `scripts/wsl/doctor_wsl.sh`
before adding any CUDA package.

`scripts/wsl/bootstrap_wsl.sh --user-only` configures the repository `.venv`
without sudo when Python 3.12, Git, CMake, and G++ already exist. It installs the
Ninja Python package into that environment. The `--install` path uses apt and
therefore requires an interactive sudo policy or a separately approved
non-interactive configuration.

WSL is suited to Linux builds, offline ROS compilation, Python/C++, containers,
and GPU compute. Real robot Ethernet, industrial USB cameras, serial/CAN, and
DDS-heavy field validation remain Ubuntu-laptop responsibilities.

The 512x512 float32 CUDA smoke operation completed on the RTX 4070 Ti with the
same deterministic checksum as Windows native. Local reports are stored under
`~/robotics-data/benchmarks`, outside Git.
