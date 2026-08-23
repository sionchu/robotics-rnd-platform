# NVIDIA CUDA and TensorRT

| Field | Value |
|---|---|
| Title | CUDA Toolkit documentation |
| Provider | NVIDIA |
| URL | https://docs.nvidia.com/cuda/ |
| Purpose | Installation, programming, compiler, libraries, profiling, and release notes |
| Version/release | Latest was CUDA 13.3 when verified; select by support matrix |
| Date last verified | 2026-08-24 |
| Why it matters | Official source for reproducible GPU research |
| Learning module | `learning/12_cuda_tensorrt` |
| Project/application | Future GPU perception benchmarks |
| Local notes | Ubuntu RTX 5060 Laptop GPU and driver 580 are kernel-visible, while its Codex environment lacks host device-node access; run the documented host `nvidia-smi` gate there. Windows/WSL RTX 4070 Ti telemetry and PyTorch CUDA 13.0 smoke tests pass with driver 591.86. Native `nvcc` remains a separate absent Toolkit component. |

| Field | Value |
|---|---|
| Title | CUDA Installation Guide for Linux |
| Provider | NVIDIA |
| URL | https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html |
| Purpose | Separates driver validation, runtime libraries, Toolkit, and compiler installation |
| Version/release | 13.3 documentation when verified |
| Date last verified | 2026-08-24 |
| Why it matters | Prevents treating absent `nvcc` as an NVIDIA driver failure |
| Learning module | `learning/12_cuda_tensorrt` |
| Project/application | `docs/setup/NVIDIA_GPU_STATUS.md` and future GPU benchmarks |
| Local notes | No Ubuntu system CUDA/driver package was installed during v0.2. Windows native also retains no `nvcc`; WSL PyTorch libraries live in the repository `.venv`, not the system driver stack. |

## CUDA on WSL

| Field | Value |
|---|---|
| Title | CUDA on WSL User Guide |
| Provider | NVIDIA |
| URL | https://docs.nvidia.com/cuda/wsl-user-guide/index.html |
| Date last verified | 2026-08-24 |
| Local notes | Ubuntu 24.04 under WSL2 sees the RTX 4070 Ti through the Windows driver. Do not install a Linux display driver inside WSL. Use only WSL-specific/toolkit-only packages when a compiler is needed. |

| Field | Value |
|---|---|
| Title | NVIDIA TensorRT documentation |
| Provider | NVIDIA |
| URL | https://docs.nvidia.com/deeplearning/tensorrt/latest/index.html |
| Purpose | ONNX import, engine build/runtime, quantization, profiling, and migration |
| Version/release | Latest was 11.2.1 when verified; Jetson support is JetPack-specific |
| Date last verified | 2026-08-24 |
| Why it matters | Converts measured model baselines into hardware-specific inference engines |
| Learning module | `learning/12_cuda_tensorrt` |
| Project/application | Future laptop/Jetson inference comparison |
| Local notes | Never commit engine files; benchmark accuracy as well as latency/throughput |
