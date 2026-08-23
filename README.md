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
python -m pip install -e ".[dev,vision]"
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

## Start a research experiment

```bash
python scripts/new_experiment.py "camera calibration baseline"
```

Fill in the question, hypothesis, environment, reproduction steps, metrics,
results, and conclusion before promoting code. See `RESEARCH_WORKFLOW.md`.

## Repository map

- `src/robotics_rnd/core`: stable units, frames, geometry, config, diagnostics, and state.
- `src/robotics_rnd/robot`, `vision`: platform-owned interfaces and data models.
- `src/robotics_rnd/skills`: reusable behavior composed from interfaces.
- `src/robotics_rnd/drivers`: mocks, replay, and optional vendor adapters.
- `applications`: runnable composition roots and future labs.
- `experiments`, `learning`, `resources`: the research and retention workflow.
- `hardware`, `simulation`, `integrations`: optional environment-specific boundaries.
- `tests`: unit, integration, and enforceable architecture constraints.

Read `ARCHITECTURE.md`, `SECURITY_AND_IP.md`, and `AGENTS.md` before extending
the platform. The next recommended milestone is live-camera validation using a
generic image-source adapter and a physically printed target; robot motion
remains out of scope until perception uncertainty is measured on real optics.
