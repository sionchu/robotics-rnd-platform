# Vision Foundation to Robot Guidance

## Reusable frame path

```text
ImageSource
  -> AprilTag detector
  -> pixel corners + quality
  -> calibrated PnP
  -> T_camera_target
  -> T_robot_camera @ T_camera_target
  -> T_robot_target
  -> guidance quality/safety gate
  -> RobotInterface
```

The v0.2 milestone validates only the path through `T_robot_target`. It does not
authorize robot motion. A future application must separately validate physical
camera calibration, target quality thresholds, robot state, workspace limits,
collision behavior, stop/fault handling, and operator approval.

Reusable v0.2 components are `CameraModel`, calibration persistence,
`ImageSource`, image replay/synthetic generation, `AprilTagObservation`, the PnP
result, reprojection/pose metrics, `Transform`, frame semantics, and the existing
`VisionInterface` boundary.

## RB guidance path

```text
Camera
  -> generic observation
  -> T_camera_target
  -> T_robot_camera
  -> T_robot_target
  -> Guidance Skill
  -> RobotInterface
  -> RainbowRobotDriver
  -> RB Controller
```

The future Rainbow adapter translates platform metres/radians and states into a
reviewed `rbpodo` mapping. The v0.2 modules remain unaware of RB types.

## Mech-Mind paths

Direct Mech-Eye acquisition:

```text
Mech-Eye -> MechEyeDriver -> Image / Depth / PointCloud
         -> platform calibration, pose, or registration algorithms
```

External Mech-Vision results:

```text
Mech-Vision -> MechVisionProvider -> VisionObservation / VisionTarget
            -> shared transform and guidance path
```

The direct camera driver and external result provider remain distinct. Vendor
SDK values are converted at their adapters and never enter core or vision APIs.

## Raspberry Pi path

A future Raspberry Pi 4 camera adapter implements `ImageSource`. The detector,
PnP, replay format, calibration JSON, and benchmark schema should remain
unchanged. The first deployment goal is correctness and replay parity, followed
by latency/FPS/memory measurement—not a new architecture.

## Optional ROS 2 mapping

ROS remains an integration boundary:

- `CameraModel` maps to `sensor_msgs/CameraInfo` fields `width`, `height`, `K`,
  `D`, and `distortion_model` after explicit convention validation.
- A pose in one parent frame maps to `geometry_msgs/PoseStamped` with a ROS time
  and `header.frame_id`.
- `Transform(T_target_source)` maps conceptually to `TransformStamped` with
  parent `target` and child `source`; a bridge must test TF2 lookup direction.
- Static physical calibration may be published through a TF2 static broadcaster.

No ROS import is required to run any v0.2 experiment.

## NVIDIA acceleration sequence

Correctness and CPU metrics precede acceleration:

```text
CPU OpenCV baseline
  -> measured GPU-suitable workload
  -> PyTorch GPU where relevant
  -> ONNX
  -> TensorRT
  -> Isaac ROS when a ROS graph benefits
```

AprilTag/PnP is not GPU-optimized in v0.2. The GPU host must first pass native
`nvidia-smi` validation described in `docs/setup/NVIDIA_GPU_STATUS.md`.
