# Roadmap

Statuses: `DONE`, `NEXT`, `PLANNED`, `BLOCKED-EXTERNAL`.

## Phase 0 — Platform bootstrap (`DONE`)

Ubuntu diagnostics, Git/CI, Python/C++ baselines, core models/interfaces,
mocks/replay, adapter skeletons, research workflow, migration evidence, and
hardware-free gates.

## Phase 1 — Robotics math and vision foundation (`DONE`)

Coordinate-frame exercises; camera model; OpenCV calibration; AprilTag/ArUco;
PnP; reprojection/error analysis; recorded generic fixtures; sensitivity study;
benchmark schema. Validation is synthetic/replay-only.

## Phase 1.1 — Pi Camera & Edge Vision (`BLOCKED-EXTERNAL`)

Adapter lifecycle, metadata normalization, capture/dataset/replay tooling,
calibration binding, physical protocols, experiments 006–012, deployment, and
hardware-free tests are prepared. The Pi was unreachable, so sensor/modes,
real calibration/PnP/repeatability/sensitivity, and Pi-vs-laptop measurements
remain `NOT_RUN_HARDWARE_UNAVAILABLE`. Complete the exact hardware handoff before
release tagging or physical promotion.

## Phase 2 — RB Robot Control Lab (`NEXT`)

Review supported controller and official `rbpodo` versions; safe connection and
state acquisition; capability mapping; mock/replay logs; joint/linear commands;
digital I/O; fault behavior; explicit hardware safety checklist. No live command
before those gates.

## Phase 3 — Mech-Eye / 3D Vision Lab (`PLANNED`)

Official SDK adapter in its own optional environment; acquisition contracts;
depth/point clouds; calibration; ROI; normals; generic pose, registration, and
refinement experiments. No SDK binaries or private captures in Git.

## Phase 4 — Vision-guided RB robot (`PLANNED`)

Robot-camera frame chain; physical calibration; target quality gates; guidance
skill; correction loop; mock, replay, simulation, then authorized hardware.

## Phase 5 — ROS 2 integration (`PLANNED`)

ROS 2 Jazzy bridge; TF2; rosbag2; RViz2; messages/services/actions justified by
use cases. Core remains importable without ROS.

## Phase 6 — Extended edge deployment (`PLANNED`)

After v0.2.1 physical evidence: extended Pi accuracy/dynamics, optional ROS 2
image bridge, additional edge targets, profiling, and deployment hardening.

## Phase 7 — GPU robotics (`BLOCKED-EXTERNAL`)

PyTorch, CUDA profiling, ONNX, TensorRT, and Isaac ROS. An RTX 5060 Laptop GPU
and driver 580 are kernel-visible, but the Codex environment hides native device
nodes. Complete the documented host `nvidia-smi` gate before GPU benchmarks.

## Phase 8 — Simulation and digital twin (`PLANNED`)

Gazebo, OpenUSD, Isaac Sim only when hardware supports it, robot/camera
simulation, replay, and sanitized synthetic datasets.

## Phase 9 — Manipulation and autonomy (`PLANNED`)

MoveIt 2; Nav2 where relevant; reusable calibration/localization/guidance/
alignment/inspection/path-correction skills; expanded simulation gates.

## Phase 10 — Physical AI and portfolio (`PLANNED`)

Sim-to-real and imitation/VLA experiments with benchmarked, separately reviewed,
company-IP-free standalone repositories.
