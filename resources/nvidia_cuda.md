# NVIDIA CUDA and TensorRT

| Field | Value |
|---|---|
| Title | CUDA Toolkit documentation |
| Provider | NVIDIA |
| URL | https://docs.nvidia.com/cuda/ |
| Purpose | Installation, programming, compiler, libraries, profiling, and release notes |
| Version/release | Latest was CUDA 13.3 when verified; select by support matrix |
| Date last verified | 2026-08-23 |
| Why it matters | Official source for reproducible GPU research |
| Learning module | `learning/12_cuda_tensorrt` |
| Project/application | Future GPU perception benchmarks |
| Local notes | RTX 5060 Laptop GPU and driver 580 are kernel-visible; Codex lacks host `/dev` access, so native `nvidia-smi` remains a manual gate. `nvcc` is a separate absent Toolkit component. |

| Field | Value |
|---|---|
| Title | CUDA Installation Guide for Linux |
| Provider | NVIDIA |
| URL | https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html |
| Purpose | Separates driver validation, runtime libraries, Toolkit, and compiler installation |
| Version/release | 13.3 documentation when verified |
| Date last verified | 2026-08-23 |
| Why it matters | Prevents treating absent `nvcc` as an NVIDIA driver failure |
| Learning module | `learning/12_cuda_tensorrt` |
| Project/application | `docs/setup/NVIDIA_GPU_STATUS.md` and future GPU benchmarks |
| Local notes | No CUDA or driver package was installed during v0.2 |

| Field | Value |
|---|---|
| Title | NVIDIA TensorRT documentation |
| Provider | NVIDIA |
| URL | https://docs.nvidia.com/deeplearning/tensorrt/latest/index.html |
| Purpose | ONNX import, engine build/runtime, quantization, profiling, and migration |
| Version/release | Latest was 11.2.1 when verified; Jetson support is JetPack-specific |
| Date last verified | 2026-08-23 |
| Why it matters | Converts measured model baselines into hardware-specific inference engines |
| Learning module | `learning/12_cuda_tensorrt` |
| Project/application | Future laptop/Jetson inference comparison |
| Local notes | Never commit engine files; benchmark accuracy as well as latency/throughput |
