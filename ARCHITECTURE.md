# Architecture

## Purpose

The platform is a reusable robotics research substrate, not an application and
not a vendor SDK wrapper. Applications depend inward on stable contracts; vendor
and framework integrations depend outward on those contracts.

```text
Applications / experiments
          |
          v
Reusable skills and workflows
          |
          v
Robot + vision interfaces ----- core geometry/models/state
          ^
          |
Drivers and integrations (ROS 2, TCP, GUI, vendor SDKs)
```

## Dependency rules

1. `robotics_rnd.core` depends only on the Python standard library and NumPy.
2. `robotics_rnd.robot` and `robotics_rnd.vision` depend on core contracts, not
   on drivers. Vision may use NumPy and its explicit optional OpenCV dependency;
   raw OpenCV values are converted before reaching core or public observations.
3. Skills depend on interfaces, never concrete hardware adapters.
4. Drivers may depend on vendor SDKs, but their public methods accept and return
   platform models only.
5. ROS 2, TCP, GUI, Raspberry Pi, CUDA, and Isaac code lives under integrations
   or drivers and is always optional.
6. Applications are composition roots. They choose interfaces, adapters, skills,
   configuration, and logging.
7. Tests must be able to validate the generic platform without hardware, ROS,
   CUDA, or vendor SDKs.

Architecture tests scan core imports for `rclpy`, `rbpodo`, Mech-Eye modules,
Raspberry Pi modules, OpenCV, and CUDA/Isaac dependencies.

## Coordinate and unit convention

- Internal translation and position: meters (`m`).
- Joint and angular values: radians (`rad`).
- Time: seconds and timezone-aware UTC timestamps.
- Quaternion public order: `(x, y, z, w)` and normalized.
- Right-handed Cartesian frames unless a documented adapter converts otherwise.
- A transform named `T_target_source` maps coordinates expressed in `source`
  into `target`.
- Pose and point transformations reject frame mismatches rather than guessing.
- Vendor/UI units are converted explicitly at adapter boundaries.

## Python, C++, and Bash policy

- Python: research, experiments, AI, orchestration, and initial contracts.
- C++17: performance-critical robotics, production nodes, and low-latency paths.
- Bash: conservative environment, deployment, and automation entry points.

The C++ project remains independent from ROS and does not duplicate the Python
platform wholesale.

## Hardware boundaries

`RobotInterface` exposes capability discovery and generic state/command/result
models. `MockRobot` proves the contract. `RainbowRobotDriver` is an explicit safe
skeleton; `rbpodo` must never leak through its public API.

`VisionInterface` returns vendor-neutral observations. `MockVision` and
`ReplayVision` prove deterministic behavior. Direct Mech-Eye capture and
Mech-Vision result-provider paths are separate adapters because they own
different responsibilities.

The v0.2 image path is `ImageSource -> detector -> pose estimator -> Transform
-> metrics`. Camera arrays and OpenCV `rvec/tvec` stay within the vision package.
Calibration and tag geometry use metres; image coordinates and reprojection use
pixels. See `docs/research/VISION_FOUNDATION_PROMOTION.md` for evidence and
limitations of each promoted component.

The v0.2.1 edge path adds `Picamera2 -> PiCameraSource -> ImageFrame +
CaptureMetadata -> dataset/replay`. Picamera2 is imported lazily only under
`drivers/raspberry_pi`; generic camera, calibration, dataset, analysis, and pose
models contain no Pi object. Capture, stored, and algorithm resolutions are
separate. Calibration provenance binds sensor class, mode, resolution, pixel
format, and crop; pure full-frame resize scales intrinsics only through a tested
explicit helper. Hardware absence never blocks core, replay, or CI.

Raspberry Pi and Jetson are deployment targets. ROS 2 and Isaac ROS are
integrations. The repository must remain useful when all of them are absent.

## Research-to-application boundary

Experiments retain hypotheses, environment, metrics, results, and conclusions.
Only validated work with stable tests graduates into `src/robotics_rnd`. Skills
then compose interfaces into reusable behavior; applications supply concrete
drivers. See `RESEARCH_WORKFLOW.md`.

## Repository separation

KAI Robotics Vision remains an external repository/snapshot. This repository has
no reverse dependency on it, no imported history, and no copied implementation
or operational assets. A future organizational consumer should use a reviewed,
versioned release of the generic platform rather than source-tree coupling.
