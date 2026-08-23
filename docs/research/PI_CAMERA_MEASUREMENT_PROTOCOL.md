# Raspberry Pi Camera Measurement Protocol

## Purpose and result honesty

This protocol converts the v0.2 synthetic vision foundation into auditable
physical evidence without claiming more accuracy than the fixtures support.
Every result declares one ground-truth class:

- `MEASURED_PHYSICAL_REFERENCE`: ruler/tape/protractor value with uncertainty.
- `NOMINAL_PHYSICAL_REFERENCE`: positioned nominally but not measured reliably.
- `NO_GROUND_TRUTH_REPEATABILITY_ONLY`: stationary-series variation only.
- `ALGORITHM_GROUND_TRUTH`: same-input cross-host numerical equivalence.

Reprojection error is always a solver/image residual, not physical pose truth.

## Equipment and setup

1. Rigidly mount the camera; do not hand-hold accuracy runs.
2. Rigidly mount the target on a planar backing.
3. Generate the tag with `scripts/generate_apriltag_target.py`, print at 100%,
   disable fit-to-page, verify the 100 mm reference, and measure the outer black
   tag square in at least two directions.
4. Record measuring tool, smallest readable increment, estimated manual
   uncertainty, and camera distance reference point in a copy of
   `experiments/vision/_physical_measurement_template.yaml`.
5. Keep the camera fixed between calibration and pose validation unless the
   experiment explicitly studies remounting.
6. Avoid glare, flickering illumination, loose cables, unstable Pi power, or
   unsafe high-intensity lighting.

A household ruler/tape is not precision metrology. Do not report sub-millimetre
accuracy when the physical reference uncertainty is millimetres.

## Environment registration

Run `scripts/pi/doctor_pi.sh` and keep its sanitized output with the local
dataset. Record exact sensor, modes, OS, kernel, Python, Picamera2,
`rpicam-apps`, libcamera context, and OpenCV. Do not copy serials, addresses,
hostnames, MAC addresses, or SSH details into results.

Select one full-frame/no-custom-crop mode for the initial lab. Record capture,
stored, and algorithm resolution separately. A calibration is bound to its
sensor, mode, capture resolution, pixel format, and crop state.

## Camera controls

First capture an auto sequence after at least 20 warm-up frames. Inspect
exposure, analogue/digital gain, colour gains, lens position where supported,
frame duration, and timing. Then repeat with stable values locked where the
detected controls permit. Never request autofocus from a fixed-focus camera.

Change only one study factor at a time where practical. If auto behavior changes
between frames, classify that as a capture-pipeline effect rather than an
AprilTag algorithm effect.

## Calibration capture

Use at least 20 accepted views per run with centre, left/right, top/bottom,
near/far, positive/negative tilt, and roll coverage. Document rejection rules
before excluding images. Build at least three independent subsets/runs.

Record each run's `fx`, `fy`, `cx`, `cy`, distortion vector, accepted/rejected
views, RMS/mean/max and per-view reprojection. Report between-run variation.
Persist a provenance-bound calibration artifact; mismatched sensor/mode/
resolution/crop use must fail. Pure full-frame resize may use the tested
intrinsic scaling helper only when aspect ratio is preserved.

## AprilTag and PnP

Use `tag36h11`, id 7, and the measured black outer-square size in metres. The
corner order remains TL, TR, BR, BL and PnP returns `T_camera_tag`. Record
detection success, tag edge pixels, reprojection, translation/orientation,
capture metadata, setup distance/angle, and ground-truth class.

## Repeatability and sensitivity

- Static repeatability: 200 controlled frames at one rigid pose.
- Distance: 100 frames at each feasible measured distance.
- Angle: 100 frames at each reproducible nominal/measured angle.
- Capture conditions: matched 100-frame safe illumination/exposure/blur runs.

Retain failed frames. Report detection success, translation RMS/axis jitter,
orientation deviation, corner RMS jitter, frame interval mean/std, and
reprojection. Keep camera effects, timing effects, and algorithm effects
separate where evidence permits.

## Pi vs laptop replay

Process the exact same transferred PNG/metadata dataset with the same
calibration, measured tag size, family/id, and algorithm resolution. Record
OpenCV/Python/platform versions, warm-up, CPU/memory method, latency, FPS, and
thermal/background-load notes. Compare detection decisions, corner pixels,
translation, orientation, and reprojection with explicit tolerances.

Do not add network streaming, GPU, ROS image transport, or different capture
inputs to this comparison.
