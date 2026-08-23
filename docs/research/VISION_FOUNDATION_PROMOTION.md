# Vision Foundation Promotion Record

Date: 2026-08-23. All evidence is synthetic/replay-only.

| Promoted component | Origin | Validation evidence | API responsibility | Assumptions | Known limitations |
|---|---|---|---|---|---|
| `camera.models` | Experiment 001 | Noisy known-intrinsics calibration and model validation tests | Explicit image size, intrinsics, distortion, frame | Pinhole/OpenCV distortion convention | No physical optics validation |
| `calibration.checkerboard` | Experiment 001 | 28-view study: 0.1832 px mean reprojection; <0.1% focal errors | Estimate intrinsics from metric checkerboard points and pixel observations | Diverse views; fixed `k3`; >=8 observations | No image corner extractor or outlier rejection |
| `calibration.io` | Experiment 001 | JSON round-trip test and tracked calibration result | Portable, validated calibration persistence | Schema v1, ISO timestamp, SI/pixel metadata | JSON migration policy not yet established |
| `camera.sources/replay/synthetic` | Experiments 001–002 | Determinism, reset/exhaustion, fixture reproduction | Hardware-free image/observation inputs | In-memory uint8 frames; seeded generators | No video/live source or timing model |
| `detection.AprilTagObservation` | Experiment 002 | Model/corner-order tests; eight scenario detections | Neutral family/id/corners/frame/time/quality | Clockwise TL/TR/BR/BL corners | No decision margin; one-tag study |
| `detection.OpenCvAprilTagDetector` | Experiment 002 | 8/8 synthetic success; no-tag and family tests | Contain OpenCV and return platform models | Grayscale/BGR/BGRA uint8; OpenCV dictionaries | Synthetic only; no occlusion/physical lighting gate |
| `pose.conversions` | Experiment 003 | Exact matrix/pose tests and `T_camera_tag` assertions | Convert OpenCV object-to-camera values to platform transforms | Metres; camera x-right/y-down/z-forward | Requires explicit tag frame convention |
| `pose.pnp` | Experiment 003 | Four exact poses at numerical precision; raster integration | Planar tag PnP and reprojection result | Known size; calibrated camera; ordered corners | Planar ambiguity; limited fallback policy |
| `pose.uncertainty` | Experiments 003/005 | Truth comparisons across 450+ PnP trials | Translation/orientation/reprojection error metrics | Matching frames and ground truth | Not a probabilistic covariance model |
| `vision.benchmark` | Experiments 002/005 | Portable JSON record and validation test | Cross-host latency/FPS/success/accuracy schema | Sanitized host descriptions | No controlled multi-host benchmark yet |
| Core `Transform` convention | Experiment 004 | 100 cases; max errors below `9e-16`; reversed chain rejected | `T_target_source` composition/inverse | Rigid right-handed transforms | Not physical extrinsic calibration |

Promotion means the API is reusable for continued research. It does not mean
hardware accuracy, production safety, or vendor compatibility is established.

## v0.2.1 preparation disposition

Hardware-independent additions—capture metadata, dataset validation/replay,
calibration configuration binding, pure-resize intrinsic scaling, repeatability,
and pose-run equivalence—have deterministic unit tests and are reusable research
infrastructure. `PiCameraSource`, remote deployment, capture controls, and every
experiment 006–012 result remain `CONTINUE_RESEARCH`: no Pi or camera was
reachable, so no hardware-specific component is promoted as validated and no
physical performance claim is made.
