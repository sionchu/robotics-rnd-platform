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

The v0.2.1 prepared path is:

```text
Picamera2 -> PiCameraSource -> ImageFrame + CaptureMetadata
           -> AprilTag -> PnP -> T_camera_tag -> Quality/Result
Captured dataset -> DatasetImageSource -> same detector/PnP/result
```

The adapter, capture schema, calibration binding, replay, repeatability, and
cross-host comparison are implemented and hardware-free tested. The Pi was not
reachable, so sensor/modes, real frames, accuracy, latency, and replay parity
remain unvalidated. These components do not authorize RB motion.

For RB reuse, physical Pi evidence will characterize generic camera uncertainty.
v0.3 must independently validate RB state/command/fault/safety behavior. Only
after both labs pass should `T_base_camera @ T_camera_target` feed a reviewed
guidance skill and command gate.

For Mech-Mind reuse, Pi-specific ISP/control observations do not transfer, but
dataset provenance, timestamp honesty, replay, pose/transform quality, ground-
truth classification, sensitivity design, and cross-host comparison do. A
future `MechEyeDriver` supplies image/depth/point-cloud data through its own
adapter while downstream transform/quality/guidance contracts remain stable.

The same generic frame/result contracts can later move from Pi CPU to Jetson.
Correctness, capture control, and replay evidence precede CUDA/TensorRT work.

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

The future edge mapping is `PiCameraSource -> ImageFrame -> optional ROS 2
sensor_msgs/Image + CameraInfo`; pose maps separately to `PoseStamped` or
`TransformStamped`. ROS 2 remains optional and is not installed on the Pi for
v0.2.1 preparation.

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
