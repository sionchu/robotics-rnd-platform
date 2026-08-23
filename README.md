# Robotics R&D Platform

A private, vendor-independent foundation for robotics learning, experiments,
reusable skills, and future applications. Version 0.2 adds a measured CPU vision
foundation—camera calibration, AprilTag detection, PnP pose, transform-chain
validation, and sensitivity analysis—while preserving the v0.1 architecture.

This repository is not KAI Robotics Vision, contains none of its source/history
or operational data, and does not claim live robot or camera validation.

## Current capabilities

- meter/radian/XYZW geometry with explicit `FrameId` and `T_target_source` rules;
- generic `RobotInterface`, commands, state, results, and capability discovery;
- deterministic `MockRobot` with connect, joint/linear target, stop, fault, and reset behavior;
- generic `VisionInterface`, observations, targets, quality metrics, mock and replay providers;
- generic job state machine with invalid-transition, fault, stop, and recovery paths;
- safe Rainbow, direct Mech-Eye, and Mech-Vision provider skeletons that fail clearly;
- mock vision-to-transform-to-robot integration example;
- explicit pinhole camera/intrinsic/distortion models and portable calibration JSON;
- deterministic checkerboard calibration with per-view reprojection metrics;
- OpenCV AprilTag detection returning platform-owned corners and quality values;
- planar PnP producing tested `T_camera_tag` transforms and pose-error metrics;
- synthetic/replay images, compact generated fixtures, and five complete research experiments;
- portable CPU/GPU/edge benchmark-result schema with no fabricated GPU results;
- Python quality gates, architecture-boundary tests, and independent C++17 CMake/CTest baseline;
- separate Ubuntu, Windows native, and WSL2 diagnostics/bootstrap paths with one Git history;
- bounded Windows/WSL PyTorch CUDA smoke reporting and an optional OpenUSD 26.8 experiment;
- versioned JSON/YAML Workcell Exchange manifests with core-validated frame graphs;
- manifest-driven metric OpenUSD workcells with `/World`, `/Robot`, `/Camera`, `/Fixture`, and `/Target`;
- experiment template, learning roadmap, hardware notes, and curated official resources.

## Quick start

Ubuntu 24.04 and Python 3.12 are the baseline. Preview the conservative bootstrap:

```bash
./scripts/bootstrap_ubuntu.sh --dry-run
```

For an existing compatible workstation, create a local environment without
system changes:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,vision,workcell]"
```

Run the generic gates and examples:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy
python scripts/doctor.py
python -m applications.vision_lab.mock_guidance
python -m robotics_rnd.vision calibration
python -m robotics_rnd.vision apriltag
python -m robotics_rnd.vision pnp
python -m experiments.vision.run_all all
cmake -S cpp -B cpp/build -G Ninja
cmake --build cpp/build
ctest --test-dir cpp/build --output-on-failure
```

None of these commands require hardware, ROS 2, CUDA, or a vendor SDK. The
vision commands are explicitly synthetic/replay validation.

For the optional schema-to-OpenUSD path, install the two explicit extras and
generate an ignored local artifact:

```bash
python -m pip install -e ".[workcell,openusd]"
python experiments/openusd/create_stage.py --manifest config/workcells/minimal-workcell.yaml
```

Windows uses the independent clone at `C:/dev/robotics-rnd-platform`. Preview
its conservative setup and run the read-only doctor with:

```powershell
pwsh -File scripts/windows/bootstrap_windows.ps1 -Mode Preview
pwsh -File scripts/windows/doctor_windows.ps1
```

WSL2 keeps its clone under `~/robotics/robotics-rnd-platform`. Use
`scripts/wsl/bootstrap_wsl.sh --user-only` when Python 3.12, Git, CMake, and G++
already exist and apt/sudo installation is not desired. See
`docs/workstations/OVERVIEW.md`.

## Start a research experiment

```bash
python scripts/new_experiment.py "camera calibration baseline"
```

Fill in the question, hypothesis, environment, reproduction steps, metrics,
results, and conclusion before promoting code. See `RESEARCH_WORKFLOW.md`.

## Repository map

- `src/robotics_rnd/core`: stable units, frames, geometry, config, diagnostics, and state.
- `src/robotics_rnd/robot`, `vision`: platform-owned interfaces and data models.
- `src/robotics_rnd/exchange`, `schemas`: validated vendor-neutral interchange contracts.
- `src/robotics_rnd/skills`: reusable behavior composed from interfaces.
- `src/robotics_rnd/drivers`: mocks, replay, and optional vendor adapters.
- `applications`: runnable composition roots and future labs.
- `experiments`, `learning`, `resources`: the research and retention workflow.
- `hardware`, `simulation`, `integrations`: optional environment-specific boundaries.
- `tests`: unit, integration, and enforceable architecture constraints.

Read `ARCHITECTURE.md`, `SECURITY_AND_IP.md`, and `AGENTS.md` before extending
the platform. The Workcell Exchange format is documented in
`docs/architecture/WORKCELL_EXCHANGE_SCHEMA.md`. Live-camera and robot-motion
work remains outside this manifest-only interoperability checkpoint.
