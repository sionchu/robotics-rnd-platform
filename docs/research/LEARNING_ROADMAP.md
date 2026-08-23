# Learning Roadmap

Statuses describe repository evidence, not the user's personal mastery:
`NOT_STARTED`, `REFERENCE_CREATED`, `EXPERIMENT_AVAILABLE`,
`USER_STUDY_PENDING`, `APPLIED`.

| Priority | Topic | Repository status | Evidence / next user exercise | Platform use |
|---|---|---|---|---|
| 1 | Linux and Git workflow | USER_STUDY_PENDING | Reproduce branch, commit, recovery, permissions, and service exercises | Safe daily engineering |
| 2 | Python engineering | EXPERIMENT_AVAILABLE | Extend a typed model and tests without violating boundaries | Core and experiments |
| 3 | Modern C++17 | USER_STUDY_PENDING | Extend the independent CMake geometry target | Low-latency paths |
| 4 | Pinhole camera model | EXPERIMENT_AVAILABLE | Derive `u=fx*x/z+cx`, then vary focal length in experiment 001 | Camera foundation |
| 5 | Intrinsic matrix | APPLIED | Explain each `K` entry and reproduce the ground-truth comparison | Calibration/PnP |
| 6 | Lens distortion | EXPERIMENT_AVAILABLE | Plot radial/tangential displacement and evaluate model order | Calibration quality |
| 7 | Camera extrinsics | EXPERIMENT_AVAILABLE | Derive object-to-camera `R,t` for a synthetic board/tag | Robot-camera chain |
| 8 | Homogeneous transforms | APPLIED | Reproduce experiment 004 and explain composition order | All robotics work |
| 9 | Rotation matrix | APPLIED | Verify orthonormality/determinant and convert known axes | Pose conversion |
| 10 | Rodrigues vector | APPLIED | Convert three known `rvec` cases to matrices manually and in OpenCV | OpenCV boundary |
| 11 | Quaternion XYZW | APPLIED | Compare matrix/quaternion composition and sign equivalence | Platform transforms |
| 12 | PnP | EXPERIMENT_AVAILABLE | Reproduce exact and noisy cases; explain object-to-camera output | Pose estimation |
| 13 | Planar PnP ambiguity | EXPERIMENT_AVAILABLE | Explain the near-frontal error tail in experiment 005 | Pose quality gates |
| 14 | Reprojection error | APPLIED | Compare low residual with the biased-intrinsics pose error | Calibration/PnP metrics |
| 15 | AprilTag geometry | EXPERIMENT_AVAILABLE | Draw tag axes and justify TL/TR/BR/BL ordering | Fiducial pipeline |
| 16 | Calibration quality | EXPERIMENT_AVAILABLE | Design image-coverage and outlier-rejection extensions | Live camera readiness |
| 17 | Pose uncertainty | EXPERIMENT_AVAILABLE | Add a multifactor/covariance study without overclaiming | Guidance gating |
| 18 | ROS 2 Jazzy / TF2 | REFERENCE_CREATED | Map one platform camera/transform fixture and compare numerically | Optional integration |
| 19 | Robot interfaces and safety | USER_STUDY_PENDING | Extend mock/replay before authorized hardware | RB control lab |
| 20 | 3D vision / point clouds | NOT_STARTED | Acquisition-independent filtering/registration benchmark | Mech-Eye lab |
| 21 | CUDA / ONNX / TensorRT | NOT_STARTED | Resolve native GPU access, then benchmark a justified workload | GPU robotics |
| 22 | Simulation / Physical AI | NOT_STARTED | Reproducible simulator scenario with sim-to-real assumptions | Digital twin |
| 23 | Camera sensors and ISP | REFERENCE_CREATED | Identify the actual Pi sensor pipeline, pixel format, crop, and ISP stages | Edge capture correctness |
| 24 | Rolling shutter and motion blur | EXPERIMENT_AVAILABLE | Execute experiment 011 with controlled safe motion/exposure | Dynamic vision limits |
| 25 | Exposure, gain, white balance, focus | EXPERIMENT_AVAILABLE | Compare auto/controlled metadata without inventing unsupported focus | Repeatable imaging |
| 26 | Camera timestamps | EXPERIMENT_AVAILABLE | Compare sensor, monotonic receive, processing, and file times | Latency/jitter honesty |
| 27 | Physical calibration repeatability | EXPERIMENT_AVAILABLE | Run three measured-target calibration subsets | Real intrinsic evidence |
| 28 | Printed-target and measurement uncertainty | REFERENCE_CREATED | Print/measure the tag and justify reported significant figures | Ground-truth honesty |
| 29 | ARM64 packaging and remote Linux | EXPERIMENT_AVAILABLE | Dry-run wheel/rsync, inspect, deploy, fetch without credentials | Edge portability |
| 30 | Latency versus throughput | EXPERIMENT_AVAILABLE | Run identical Pi/laptop replay with warm-up and resource notes | Edge benchmark design |

Each topic follows: theory -> runnable example -> user exercise -> experiment ->
project application. Codex implementation alone never marks user study complete.
