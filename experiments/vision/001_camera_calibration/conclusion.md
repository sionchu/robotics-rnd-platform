# Conclusion

## Question

Can the platform estimate camera intrinsics reproducibly and quantify quality
using synthetic observations?

## Hypothesis

Focal error below 0.5%, principal-point error below 2 px, distortion L2 error
below 0.02, and mean reprojection below 0.3 px.

## Method

Projected a centred 9x6-inner-corner checkerboard with 30 mm squares into 28
diverse views using fixed ground truth, then added seeded 0.15 px corner noise
and calibrated with OpenCV 4.14.0.

## Environment

Ubuntu 24.04, Python 3.12.3, NumPy, CPU OpenCV 4.14.0; no camera, ROS, or GPU.

## Data

Generated numerical observations, seed `20260823`; no external or private data.

## Metrics

Relative focal error, principal-point error, distortion L2 error, RMS/mean/max
reprojection error, and per-view RMS error.

## Results

All thresholds passed. Relative focal errors were 0.09495% and 0.09414%; the
principal-point error was 0.51073 px; distortion L2 error was 0.006126; mean
reprojection error was 0.18320 px.

## Failure cases

Fewer than eight views, inconsistent image sizes, invalid point shapes/counts,
and non-finite inputs are rejected. Poor physical coverage was not evaluated.

## Limitations

Numerical corner observations omit real lens, focus, rolling-shutter, print,
lighting, and detector errors. Results do not predict physical calibration.

## Conclusion

The platform can reproducibly estimate and persist a bounded pinhole model and
report meaningful synthetic ground-truth and reprojection metrics.

## Decision

`PROMOTE_TO_PLATFORM`
