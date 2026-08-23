# Conclusion

## Question

Which real capture conditions degrade detection and pose stability?

## Hypothesis

Low-light gain/noise, long exposure motion blur, and unsupported/unstable focus
will degrade corner and pose repeatability before reprojection alone explains it.

## Hardware

`NOT_RUN_HARDWARE_UNAVAILABLE`; sensor focus capability and safe lighting setup unknown.

## Software

Capture controls and normalized exposure/gain/colour/focus metadata are prepared.

## Method

Prepared matched 100-frame condition runs, auto/controlled separation, safe
illumination notes, and metadata-correlated repeatability summaries.

## Ground truth class

`NO_GROUND_TRUTH_REPEATABILITY_ONLY` unless a separate measured pose reference is added.

## Measurement uncertainty

Uncalibrated lighting and manually induced motion are qualitative conditions;
metadata and repeatability are reported without lux/velocity accuracy claims.

## Results

`NOT_RUN_HARDWARE_UNAVAILABLE`; measurements are intentionally null.

## Failure cases

Unsafe lighting, unsupported focus, changed geometry, uncontrolled auto values,
and incomparable conditions must be excluded with reasons.

## Limitations

This bounded study does not characterize the full ISP, radiometry, rolling
shutter, or all environmental lighting.

## Conclusion

Real capture-condition failure drivers remain unknown.

## Decision

`CONTINUE_RESEARCH`
