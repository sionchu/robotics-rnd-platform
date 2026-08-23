# Experiment 001 — Synthetic Camera Calibration

Question: can the platform recover known camera intrinsics reproducibly and
quantify calibration quality from noisy, replayable checkerboard observations?

The experiment generates 28 checkerboard views from a known pinhole camera,
varies pose, coverage, tilt, and distance, then adds seeded 0.15 px Gaussian
corner noise. OpenCV `calibrateCamera` estimates the model with `k3` fixed to
avoid an unsupported high-order degree of freedom in this bounded study.

Reproduce from the repository root:

```bash
python -m experiments.vision.run_all calibration
```

Tracked JSON outputs are human-readable. This is synthetic validation and does
not claim physical-camera accuracy.
