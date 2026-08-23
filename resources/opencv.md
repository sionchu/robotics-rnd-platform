# OpenCV

| Field | Value |
|---|---|
| Title | OpenCV 4.x documentation |
| Provider | OpenCV project |
| URL | https://docs.opencv.org/4.x/ |
| Purpose | Official API and tutorials for image processing and camera geometry |
| Version/release | 4.x; pin the experiment environment |
| Date last verified | 2026-08-23 |
| Why it matters | Baseline for calibration, fiducials, PnP, and 2D vision |
| Learning module | `learning/05_opencv`, `learning/06_camera_geometry` |
| Project/application | Vision Lab and calibration lab |
| Local notes | OpenCV is optional; document BGR/RGB, pixel, distortion, and unit conventions |

| Field | Value |
|---|---|
| Title | Camera calibration tutorial |
| Provider | OpenCV project |
| URL | https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html |
| Purpose | Intrinsic/distortion calibration workflow and reprojection concepts |
| Version/release | OpenCV 4.14.0 used by v0.2 |
| Date last verified | 2026-08-23 |
| Why it matters | Source for the promoted checkerboard calibration experiment |
| Learning module | `learning/06_camera_geometry` |
| Project/application | `applications/calibration_lab` |
| Local notes | Record image set provenance and per-image/global errors; no private scenes |

| Field | Value |
|---|---|
| Title | Perspective-n-Point pose computation |
| Provider | OpenCV project |
| URL | https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html |
| Purpose | Documents object-to-camera `rvec/tvec`, methods, and IPPE square ordering |
| Version/release | OpenCV 4.14.0 used by v0.2 |
| Date last verified | 2026-08-23 |
| Why it matters | Defines the `T_camera_tag` conversion and planar solver choice |
| Learning module | `learning/06_camera_geometry` |
| Project/application | Experiment 003 and `robotics_rnd.vision.pose` |
| Local notes | OpenCV object points are metres here; IPPE order is TL, TR, BR, BL |

| Field | Value |
|---|---|
| Title | Detection of ArUco markers (including AprilTag dictionaries) |
| Provider | OpenCV project |
| URL | https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html |
| Purpose | Detector, dictionary, marker generation, and corner conventions |
| Version/release | OpenCV 4.14.0 used by v0.2 |
| Date last verified | 2026-08-23 |
| Why it matters | Supports deterministic AprilTag generation and detection with one dependency |
| Learning module | `learning/05_opencv`, `learning/06_camera_geometry` |
| Project/application | Experiment 002 and `robotics_rnd.vision.detection` |
| Local notes | Generic output contains no `cv2` detector objects |
