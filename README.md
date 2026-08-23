# Robotics R&D Platform

A private, vendor-independent foundation for robotics learning, experiments,
reusable skills, and future applications. Version 0.3 adds a reusable external
research intake and a software-validated Rainbow RB control foundation while
preserving the v0.2 vision and v0.2.1 Raspberry Pi preparation architecture.

This repository is not KAI Robotics Vision, contains none of its source/history
or operational data, and does not claim live robot or camera validation. No RB
hardware was available, so RB status is `SOFTWARE_VALIDATED` /
`HARDWARE_NOT_VALIDATED` at LEVEL 0. The Pi was unreachable during v0.2.1, so all
Pi physical experiments remain `NOT_RUN_HARDWARE_UNAVAILABLE` and untagged.

## Current capabilities

- meter/radian/XYZW geometry with explicit `FrameId` and `T_target_source` rules;
- generic `RobotInterface` with command lifecycle, connection/fault/state,
  capabilities, SI units, and application/HMI service;
- deterministic `MockRobot`, `ReplayRobot`, portable redacted JSONL journal, and
  command/state/result replay;
- generic `VisionInterface`, observations, targets, quality metrics, mock and replay providers;
- generic job state machine with invalid-transition, fault, stop, and recovery paths;
- read-only-by-default Rainbow adapter with optional lazy rbpodo boundary,
  version/feature checks, fake backend, fault injection, reconnect lockout, and
  no live CLI; direct Mech-Eye and Mech-Vision stubs remain separate;
- mock vision-to-transform-to-robot integration example;
- explicit pinhole camera/intrinsic/distortion models and portable calibration JSON;
- deterministic checkerboard calibration with per-view reprojection metrics;
- OpenCV AprilTag detection returning platform-owned corners and quality values;
- planar PnP producing tested `T_camera_tag` transforms and pose-error metrics;
- synthetic/replay images, compact generated fixtures, and five complete research experiments;
- portable CPU/GPU/edge benchmark-result schema with no fabricated GPU results;
- lazy Picamera2 adapter boundary with lifecycle, supported-control checks, and
  normalized metadata, requiring no Pi packages in normal CI;
- versioned capture dataset manifests, on-disk replay, calibration provenance,
  tested intrinsic scaling, pose repeatability, and cross-host comparison;
- safe SSH/rsync deployment/capture/fetch tools and a printable measured-size
  `tag36h11` target generator;
- experiments 006–012 fully prepared with explicit hardware-pending status and
  an exact physical lab handoff;
- external technology registries, intake workflow/templates, provenance inventory,
  current official rbpodo/rbpodo_ros2/docs evaluation, and risk/compatibility records;
- experiments 013–016 for RB pose mapping, command semantics, reconnect/faults,
  and control-box digital I/O, all source/mock-only with LEVEL 0 labels;
- RB Control Lab mock, injected-fault, and replay demos plus an exact LEVEL 1
  read-only hardware handoff;
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
python -m robotics_rnd.edge --help
python -m experiments.vision.run_all all
python -m experiments.vision.pi_edge verify-preparation
python -m experiments.robot.run_all verify
python -m robotics_rnd.rb status
python -m robotics_rnd.rb capabilities
python -m robotics_rnd.rb mock-demo
python -m robotics_rnd.rb fault-demo
cmake -S cpp -B cpp/build -G Ninja
cmake --build cpp/build
ctest --test-dir cpp/build --output-on-failure
```

None of these commands require hardware, ROS 2, CUDA, Picamera2, or a vendor
SDK. The RB CLI deliberately has no live connection/motion command. The vision
commands are synthetic/replay and the Pi verifier rejects fabricated physical
measurements.

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
- `research`, `experiments`, `learning`, `resources`: intake registries,
  reproducible studies, decisions, and retention workflow.
- `hardware`, `simulation`, `integrations`: optional environment-specific boundaries.
- `tests`: unit, integration, and enforceable architecture constraints.

Read `ARCHITECTURE.md`, `SECURITY_AND_IP.md`, `THIRD_PARTY.md`, and `AGENTS.md`
before extending the platform. Without currently available hardware, the next
software research milestone is the Mech-Eye 3D Vision Lab. Physical Pi and RB
work remain separate exact handoffs; RB LEVEL 1 is read-only and robot motion is
not authorized.
