# Workstation Capability Matrix

Status reflects the 2026-08-23 Ubuntu baseline and the 2026-08-24 Windows/WSL
inspection. Runtime-sensitive entries should be refreshed with the doctor and
benchmark scripts after driver, package, or hardware changes.

| Capability | Ubuntu laptop | Windows native | Windows WSL2 |
|---|---|---|---|
| Python core | primary, 3.12 baseline | project 3.12 required | 3.12.3 present |
| C++ core | primary | Visual Studio Build Tools | GCC/G++ 13.3 |
| Git/Codex | primary | primary | Git present |
| ROS 2 | primary, Jazzy | optional | build/offline |
| RB real robot | primary with safety gate | no | not primary |
| Mech-Eye/Zivid real | primary with vendor gate | optional SDK research | not primary |
| Raspberry Pi | primary/SSH | SSH only | SSH only |
| CUDA | driver issue at baseline | primary, driver visible | GPU telemetry visible |
| PyTorch | optional | 2.12.1+cu130 smoke passed | 2.12.1+cu130 smoke passed |
| TensorRT | optional | optional Windows/WSL | optional |
| OpenUSD | learning/support | `usd-core` 26.8 stage creation passed | support; extra not installed |
| Blender | optional | absent at inspection | not primary |
| Isaac Sim | optional/limited | installed, below official minimum GPU/VRAM | not primary |
| Digital Twin | secondary | primary | support |
| Synthetic data | optional | primary within VRAM limits | support |
| Model training | small/medium | primary within 12 GB VRAM | primary after runtime setup |
| Real hardware tests | explicitly requested | no ordinary motion tests | no ordinary motion tests |
