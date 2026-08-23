# NVIDIA GPU Status

Observed on 2026-08-23. This report contains read-only evidence collected from
the Codex execution environment. No driver, kernel, CUDA, bootloader, or package
changes were made.

## Classification

`GPU_UNKNOWN_REQUIRES_MANUAL_INTERVENTION`

The hardware and kernel driver are visible, but this process cannot test the
host device nodes. Its `/dev` is shadowed by a user-owned tmpfs, so the failed
`nvidia-smi` call is not sufficient evidence that the native host driver is
broken. Package repair or reboot would be unjustified from this environment.

## Observed evidence

| Area | Evidence | Interpretation |
|---|---|---|
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU at PCI `0000:04:00.0` (`10de:2d19`) | Discrete GPU is PCI-visible |
| Hybrid graphics | AMD integrated display device also present; PRIME mode is `on-demand` | Hybrid laptop configuration |
| Kernel | Ubuntu `6.8.0-31-generic` | Running kernel recorded |
| Driver binding | PCI device reports `Kernel driver in use: nvidia` | Device is bound to NVIDIA, not Nouveau |
| Kernel modules | `nvidia`, `nvidia_modeset`, `nvidia_drm`, and `nvidia_uvm` loaded; Nouveau not loaded | NVIDIA module stack is loaded |
| Driver version | Kernel module and user-space packages are `580.95.05` | No observed kernel/user-space version split |
| DKMS | `nvidia/580.95.05` installed for `6.8.0-31-generic` | Module exists for the running kernel |
| GPU registration | `/proc/driver/nvidia/gpus/0000:04:00.0/information` identifies the model and minor 0 | Kernel driver has registered the GPU |
| Secure Boot | UEFI `SecureBoot` variable value is `0`; `mokutil` is not installed | Secure Boot is disabled; it is not blocking the loaded module |
| User-space libraries | `libnvidia-ml.so` and `libcuda.so` are visible | Driver runtime libraries are installed; this does not prove CUDA execution |
| Device nodes | `/dev/nvidia*` and `/dev/dri` are absent inside Codex | Required device access is unavailable to this process |
| Mount boundary | A user-owned tmpfs is mounted over the host `/dev` in this process | Missing nodes may be sandbox isolation rather than a host defect |
| `nvidia-smi` | Present at `/usr/bin/nvidia-smi`, but cannot communicate | Inconclusive until run against the native host `/dev` |
| CUDA Toolkit | `nvcc` is absent | Toolkit/compiler is not installed; unrelated to driver usability |
| Docker | Absent | No container GPU validation attempted |
| Package policy | Ubuntu recommends branch 580; installed `580.95.05`, repository candidate `580.126.09` | An update exists, but no evidence justifies changing packages here |

GPU UUIDs and other serial-like identifiers were deliberately omitted.

## Actions taken

- Collected PCI, sysfs, procfs, module, DKMS, package, Secure Boot, PRIME,
  runtime-library, and device-mount evidence.
- Enhanced `scripts/doctor.py` to report GPU detection, kernel/device usability,
  `nvidia-smi`, CUDA runtime visibility, CUDA Toolkit visibility, Docker, and
  ROS 2 separately.
- Kept the v0.2 research path CPU-only.
- Did not install or update the NVIDIA driver, CUDA Toolkit, Docker, TensorRT,
  Isaac ROS, or Isaac Sim.

## Manual host verification handoff

Run these commands in a normal Ubuntu terminal, outside the Codex sandbox:

```bash
findmnt /dev
ls -l /dev/nvidia* /dev/dri
nvidia-smi
journalctl -k -b --no-pager | grep -Ei 'nvidia|nouveau|NVRM|Xid|module verification'
dkms status
```

Expected healthy state:

- `/dev` is the native `devtmpfs`, without a user-owned tmpfs shadowing it;
- `/dev/nvidiactl` and at least `/dev/nvidia0` exist;
- `nvidia-smi` reports the RTX 5060 Laptop GPU and driver version.

If those conditions pass, reclassify as `GPU_OK`. If native device nodes are
missing or `nvidia-smi` fails, retain the complete kernel-log output and diagnose
that host condition before changing packages. Check `apt-cache policy` for every
proposed package first. Do not install CUDA Toolkit as a driver repair.

## Reboot status

No reboot is requested. Current evidence does not identify a reboot-correctable
fault, and repository research does not depend on GPU access.

## Reference

- NVIDIA, *CUDA Installation Guide for Linux*, version 13.3 documentation,
  verified 2026-08-23:
  <https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html>.
  Used to keep GPU/driver checks distinct from CUDA Toolkit and `nvcc` checks.
