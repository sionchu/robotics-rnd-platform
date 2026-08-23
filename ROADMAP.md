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

## Phase 7 — GPU robotics (`PLANNED`)

Windows native and WSL2 have a bounded RTX 4070 Ti PyTorch CUDA smoke baseline.
On the Ubuntu laptop, the RTX 5060 and driver 580 are kernel-visible but the
Codex environment hides native device nodes; complete the documented host
`nvidia-smi` gate there. Continue with reproducible cross-machine CPU/GPU
comparisons, profiling, ONNX, and TensorRT only from measured workloads.

## Phase 8 — Simulation and digital twin (`PLANNED`)

The versioned Workcell Exchange Schema, JSON/YAML round trip, core transform
validation, manifest-driven OpenUSD workcell, and asset/data policy are
established. Next, add a replay mapping in a separate research cycle. Isaac Sim
remains optional and limited by the 4070 Ti 12 GB capability gate.

## Phase 9 — Manipulation and autonomy (`PLANNED`)

MoveIt 2; Nav2 where relevant; reusable calibration/localization/guidance/
alignment/inspection/path-correction skills; expanded simulation gates.

## Phase 10 — Physical AI and portfolio (`PLANNED`)

Sim-to-real and imitation/VLA experiments with benchmarked, separately reviewed,
company-IP-free standalone repositories.
