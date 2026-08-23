# Ubuntu Laptop: Real-World Robotics Lab

Ubuntu 24.04 is the hardware-facing workstation for ROS 2, TF2, real robot and
camera integration, calibration, field devices, deployment, and approved replay
capture. The existing v0.1 bootstrap established Python 3.12, GCC/G++, CMake,
Ninja, ROS 2 Jazzy, generic tests, and hardware-safe adapter boundaries.

GPU/CUDA work on this machine remains conditional on a functioning NVIDIA
driver. The 2026-08-23 baseline could not communicate with the driver, so CPU
results remain the reference until a new local diagnostic records a different
state.

Use `scripts/doctor.py` for the existing generic report and
`docs/setup/UBUNTU_WORKSTATION.md` for the full baseline. Real motion and vendor
hardware tests are never part of the default test command.
