# ROS 2 and TF2

| Field | Value |
|---|---|
| Title | ROS 2 Jazzy documentation |
| Provider | Open Source Robotics Foundation / ROS |
| URL | https://docs.ros.org/en/jazzy/ |
| Purpose | Supported Jazzy installation, concepts, tutorials, and how-to guides |
| Version/release | Jazzy Jalisco LTS |
| Date last verified | 2026-08-23 |
| Why it matters | Defines the optional middleware integration baseline |
| Learning module | `learning/07_ros2` |
| Project/application | Future `integrations/ros2`, RB/vision bridges |
| Local notes | ROS 2 Jazzy is installed under `/opt/ros/jazzy` but remains optional and unsourced by default |

| Field | Value |
|---|---|
| Title | `tf2_ros` Jazzy documentation |
| Provider | ROS |
| URL | https://docs.ros.org/en/jazzy/p/tf2_ros/ |
| Purpose | ROS bindings and API reference for transform trees |
| Version/release | Jazzy package docs |
| Date last verified | 2026-08-23 |
| Why it matters | Bridges platform frame conventions to ROS TF2 |
| Learning module | `learning/08_tf2` |
| Project/application | Future visualization, calibration, and ROS frame bridge |
| Local notes | Compare TF2 results against core geometry tests before integration |

| Field | Value |
|---|---|
| Title | `sensor_msgs/CameraInfo` Jazzy message |
| Provider | ROS |
| URL | https://docs.ros.org/en/jazzy/p/sensor_msgs/msg/CameraInfo.html |
| Purpose | Future mapping for image size, intrinsic matrix, and distortion |
| Version/release | Jazzy message documentation |
| Date last verified | 2026-08-23 |
| Why it matters | Maps the platform camera model without making ROS mandatory |
| Learning module | `learning/07_ros2`, `learning/08_tf2` |
| Project/application | Future optional camera bridge |
| Local notes | Bridge must validate matrix order and distortion-model equivalence |

| Field | Value |
|---|---|
| Title | `geometry_msgs/TransformStamped` Jazzy message |
| Provider | ROS |
| URL | https://docs.ros.org/en/jazzy/p/geometry_msgs/msg/TransformStamped.html |
| Purpose | Future mapping for timestamped parent/child transforms |
| Version/release | Jazzy message documentation |
| Date last verified | 2026-08-23 |
| Why it matters | Carries validated platform transforms into TF2 |
| Learning module | `learning/08_tf2` |
| Project/application | Future optional transform bridge |
| Local notes | Regression-test TF2 direction against `T_target_source` before publishing |
