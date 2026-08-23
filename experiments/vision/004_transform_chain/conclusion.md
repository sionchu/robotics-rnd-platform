# Conclusion

## Question

Does the platform compose camera observations into another frame correctly?

## Hypothesis

Composition/inverse error below `1e-12` and explicit reversed-chain rejection.

## Method

Compared `T_base_camera @ T_camera_tag` with direct 4x4 multiplication across
100 seeded mixed transforms, then inverted and recovered each input.

## Environment

Ubuntu 24.04, Python 3.12.3, NumPy; hardware-independent core geometry.

## Data

Seeded synthetic translations, axes, and rotations; seed `20260823`.

## Metrics

Maximum absolute composition and inverse-recovery matrix element errors.

## Results

Maximum errors were `8.33e-16` and `8.88e-16`. Reversed composition raised a
frame-mismatch error.

## Failure cases

Reversed and frame-incompatible chains are rejected instead of inferred.

## Limitations

This validates numerical/frame semantics, not physical camera-to-robot
extrinsic calibration.

## Conclusion

`T_base_camera @ T_camera_tag = T_base_tag` is unambiguous and numerically stable.

## Decision

`PROMOTE_TO_PLATFORM`
