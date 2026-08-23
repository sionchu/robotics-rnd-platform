# Conclusion

## Question

How repeatable and plausible is calibration on real Pi camera images?

## Hypothesis

Three independent, well-covered controlled subsets will produce compatible
intrinsics with documented reprojection and between-run variation.

## Hardware

`NOT_RUN_HARDWARE_UNAVAILABLE`; sensor, lens, focus behavior, and modes unknown.

## Software

The v0.2 OpenCV calibration and v0.2.1 provenance binding are prepared. Pi
software versions remain unknown.

## Method

Prepared coverage criteria, measured target fields, three-run comparison,
auto/controlled option, and strict sensor/mode/resolution/crop binding.

## Ground truth class

`MEASURED_PHYSICAL_REFERENCE` for measured square geometry; intrinsic truth is
not independently known.

## Measurement uncertainty

The future artifact must state measuring tool resolution and square-size
uncertainty. Reprojection error is not physical ground-truth accuracy.

## Results

`NOT_RUN_HARDWARE_UNAVAILABLE`; measurements are intentionally null.

## Failure cases

Insufficient/poor coverage, wrong square size, mixed modes, crop mismatch,
blurred corners, and unsupported resolution reuse must reject promotion.

## Limitations

Manual target measurement and a planar board cannot establish traceable camera
metrology or model unrepresented lens effects.

## Conclusion

Calibration tooling is ready, but no Pi intrinsic artifact is valid yet.

## Decision

`CONTINUE_RESEARCH`
