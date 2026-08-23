# Conclusion

## Question

How do controlled geometry and image errors change AprilTag pose accuracy?

## Hypothesis

Distance, noise, intrinsic bias, and blur will degrade pose, while near-frontal
planar views will amplify orientation ambiguity.

## Method

Ran one-factor-at-a-time seeded sweeps over four distances, four tilts, five
corner-noise levels, four intrinsic perturbations, and four blur levels. PnP
levels used 30 trials; rendered blur levels used 12 detection/PnP trials.

## Environment

Ubuntu 24.04, Python 3.12.3, NumPy, CPU OpenCV 4.14.0; no camera or GPU.

## Data

Deterministic mathematical corners and generated tag images, seed `20260823`.

## Metrics

Mean/p95 translation and orientation errors, mean reprojection error, tag edge
pixels, and detection/PnP success rate.

## Results

Distance 0.5-to-1.6 m increased mean translation error by 8.55 mm. Corner noise
0-to-2 px added 9.65 mm and produced a 36.6 deg orientation p95. A 2% intrinsic
bias added 18.48 mm. Near-frontal views were most orientation-sensitive. Blur
sigma 5 reduced the small-tag detection/PnP success rate to 25%.

## Failure cases

High blur caused detection failures. Planar ambiguity produced heavy
orientation-error tails even when reprojection residual remained modest.

## Limitations

Factors were varied mostly one at a time; sample counts are small; corner noise
is idealized; no lens, motion, rolling shutter, print, lighting, or physical
calibration effects were measured.

## Conclusion

Tag pixel scale, calibration quality, subpixel corner quality, and view geometry
must be retained as pose-quality context. Reprojection error alone is not an
accuracy guarantee.

## Decision

`CONTINUE_RESEARCH`
