# GPU Smoke Experiment

```yaml
platforms:
  ubuntu: supported
  windows: supported
  wsl: supported
requires:
  gpu: nvidia
  min_vram_gb: 1
  ros2: false
  hardware: none
```

`gpu_smoke.py` performs a bounded synthetic float32 matrix multiplication using
PyTorch CUDA and records the commit, platform, GPU, VRAM, driver, PyTorch/CUDA
runtime, checksum, elapsed time, and peak allocated memory. It does not download
models or data.

Example:

```bash
python experiments/gpu/gpu_smoke.py --require-cuda \
  --output reports/local/gpu-smoke.json
```

Local reports are ignored. Copy only reviewed aggregate values into a benchmark
document.
