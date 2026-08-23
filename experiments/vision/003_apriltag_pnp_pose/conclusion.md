# Conclusion

## Question

Can known tag geometry recover `T_camera_tag` accurately and consistently?

## Hypothesis

Exact corners will meet numerical-precision thresholds and preserve direction.

## Method

Projected a 120 mm tag from four known poses, solved planar PnP, converted
OpenCV object-to-camera `rvec/tvec` to `T_camera_tag`, and compared against truth.
One generated raster image exercised detector-to-PnP integration.

## Environment

Ubuntu 24.04, Python 3.12.3, NumPy, CPU OpenCV 4.14.0; no physical camera.

## Data

Deterministic mathematical corners and one generated AprilTag raster.

## Metrics

Absolute/relative translation error, orientation error, reprojection error, and
transform name/direction.

## Results

All exact cases passed; the worst translation error was `4.97e-11 m` and worst
reprojection was `6.04e-9 px`. The raster case produced 5.05 mm and 1.13 deg
pose error despite 0.294 px reprojection error.

## Failure cases

Invalid tag sizes and incompatible image sizes are rejected. Exactly frontal
IPPE can produce a gross ambiguous solution, so a reported iterative fallback
is used only when IPPE reprojection exceeds 5 px.

## Limitations

Four planar points retain pose ambiguity and sensitivity to subpixel errors.
The fallback does not resolve all low-residual planar ambiguities.

## Conclusion

The transform mapping is mathematically correct, while the raster result proves
that downstream quality gates must consider geometry and sensitivity, not only
solver reprojection residual.

## Decision

`PROMOTE_TO_PLATFORM`
