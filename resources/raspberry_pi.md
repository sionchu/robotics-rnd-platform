# Raspberry Pi

| Field | Value |
|---|---|
| Title | Raspberry Pi computers documentation |
| Provider | Raspberry Pi Ltd |
| URL | https://www.raspberrypi.com/documentation/computers/ |
| Purpose | OS, setup, configuration, remote access, hardware, and software entry point |
| Version/release | Current documentation |
| Date last verified | 2026-08-23 |
| Why it matters | Primary reference for the Pi 4 deployment target |
| Learning module | `learning/00_linux`, `learning/05_opencv` |
| Project/application | Future edge vision benchmark |
| Local notes | Inspect the current system first; never infer the installed OS from the board model |

| Field | Value |
|---|---|
| Title | Raspberry Pi OS downloads |
| Provider | Raspberry Pi Ltd |
| URL | https://www.raspberrypi.com/software/operating-systems/ |
| Purpose | Official current and legacy Raspberry Pi OS images and compatibility |
| Version/release | Current 64-bit release: Debian 13 Trixie, 18 June 2026, kernel 6.18; Pi 4B listed compatible |
| Date last verified | 2026-08-23 |
| Why it matters | Establishes the preferred fresh-image option without forcing re-image of a stable Pi |
| Learning module | `learning/00_linux` |
| Project/application | Pi camera node setup |
| Local notes | Preserve an existing supported working OS; document re-imaging rather than automating destructive storage changes |

| Field | Value |
|---|---|
| Title | Raspberry Pi camera software |
| Provider | Raspberry Pi Ltd |
| URL | https://www.raspberrypi.com/documentation/computers/camera_software.html |
| Purpose | Current `rpicam-apps`, libcamera, and Picamera2 workflow |
| Version/release | Current stack; legacy camera stack is unsupported |
| Date last verified | 2026-08-23 |
| Why it matters | Prevents building new experiments on deprecated camera APIs |
| Learning module | `learning/05_opencv`, `learning/06_camera_geometry` |
| Project/application | Pi camera adapter and benchmark |
| Local notes | Record camera model, resolution, exposure, and thermal/power conditions |

| Field | Value |
|---|---|
| Title | `rpicam-apps` source and status |
| Provider | Raspberry Pi Ltd |
| URL | https://github.com/raspberrypi/rpicam-apps |
| Purpose | Official libcamera-based Pi camera applications and naming/status |
| Version/release | Current main; `libcamera-*` compatibility links have been removed in favor of `rpicam-*` |
| Date last verified | 2026-08-23 |
| Why it matters | Defines `rpicam-hello --list-cameras` discovery and supported current CLI naming |
| Learning module | `learning/05_opencv`, camera edge lab |
| Project/application | Pi doctor and bring-up |
| Local notes | Record the installed Pi version rather than assuming repository main |

| Field | Value |
|---|---|
| Title | The Picamera2 Library Guide |
| Provider | Raspberry Pi Ltd |
| URL | https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf |
| Purpose | Official Python API, configuration, controls, requests, metadata, and capture guidance |
| Version/release | Release 3, build date 30 June 2026, build `ca0fec80aab2` |
| Date last verified | 2026-08-23 |
| Why it matters | Primary adapter reference for request-scoped array/metadata capture and control discovery |
| Learning module | Camera controls, timestamps, edge deployment |
| Project/application | `PiCameraSource` adapter |
| Local notes | Picamera2 remains a Pi adapter dependency; current GitHub release observed as 0.3.36, but record the installed package |

| Field | Value |
|---|---|
| Title | libcamera documentation |
| Provider | libcamera project |
| URL | https://docs.libcamera.org/master/ |
| Purpose | Linux camera stack, sensor/ISP pipeline, streams, controls, crop, and scaling model |
| Version/release | Master documentation observed as v0.7.2 development documentation |
| Date last verified | 2026-08-23 |
| Why it matters | Explains why sensor mode, ISP, crop, scale, and controls are part of calibration/capture provenance |
| Learning module | Camera sensor and ISP fundamentals |
| Project/application | Pi camera measurement protocol and future camera adapters |
| Local notes | Use Raspberry Pi-supported packaged libcamera on the Pi; do not replace it ad hoc |

| Field | Value |
|---|---|
| Title | ROS 2 Jazzy on Raspberry Pi |
| Provider | Open Source Robotics Foundation / ROS |
| URL | https://docs.ros.org/en/jazzy/How-To-Guides/Installing-on-Raspberry-Pi.html |
| Purpose | Future supported approaches for ROS 2 on Raspberry Pi |
| Version/release | Jazzy documentation; future reference only |
| Date last verified | 2026-08-23 (URL verified; automated content access was blocked) |
| Why it matters | Preserves a future ROS edge path without making ROS a v0.2.1 Pi requirement |
| Learning module | `learning/07_ros2` |
| Project/application | Future optional ROS 2 edge camera bridge |
| Local notes | Keep laptop ROS 2 Jazzy authoritative until a real Pi integration requirement exists |
