# Experiment 002 — AprilTag Detection

Question: can a CPU-only detector recover a known tag from deterministic image
input and return a vendor-independent observation with quality metadata?

OpenCV's maintained AprilTag dictionaries and `ArucoDetector` were selected to
reuse the existing calibration dependency. Alternatives requiring a second
AprilTag binding were rejected because they add packaging complexity without a
demonstrated requirement. The chosen installed dependency is
`opencv-python-headless==4.14.0.94` (`cv2` 4.14.0).

```bash
python -m experiments.vision.run_all apriltag
```

The six tracked fixtures are generated locally and cover scale, translation,
rotation, perspective, and blur. Noise cases are generated during reproduction
but not stored because noise-dominated PNGs are unnecessarily large.
