# Conclusion

## Question

What repeatability does the stationary real camera/tag pipeline achieve?

## Hypothesis

Controlled capture will reduce metadata and pose variation relative to auto
capture while retaining a high detection rate.

## Hardware

`NOT_RUN_HARDWARE_UNAVAILABLE`; no stationary physical setup was observed.

## Software

Tag detection, PnP, capture metadata, pose samples, and repeatability analysis
are implemented; Pi versions remain unknown.

## Method

Prepared a 200-frame controlled sequence, per-frame failures, corner/pose/
reprojection metrics, and distinct sensor/monotonic/processing timing.

## Ground truth class

`NO_GROUND_TRUTH_REPEATABILITY_ONLY`; the fixed first/mean pose is not accuracy
ground truth.

## Measurement uncertainty

Repeatability is limited by mount stability and timing semantics. Absolute pose
accuracy requires a separately measured reference.

## Results

`NOT_RUN_HARDWARE_UNAVAILABLE`; measurements are intentionally null.

## Failure cases

Detection dropouts, ambiguous planar solutions, exposure/focus variation,
timestamp gaps, dropped frames, and mount motion must remain visible.

## Limitations

One stationary pose cannot characterize distance, angle, calibration accuracy,
or dynamic motion.

## Conclusion

The analysis path is prepared but physical repeatability is unknown.

## Decision

`CONTINUE_RESEARCH`
