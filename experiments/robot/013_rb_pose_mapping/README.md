# Experiment 013 — RB Pose Mapping

## Question

Can platform `Pose` values be converted to and from the documented rbpodo
`[x,y,z,rx,ry,rz]` representation without unit, order, or convention ambiguity?

## Hypothesis

SI↔vendor translation will round-trip below `1e-9 mm`, rotations will round-trip
as matrices including gimbal-sensitive cases, and non-finite values will fail.

## Sources

Rainbow Robotics rbpodo API/source and official coordinate-system documentation,
recorded in `docs/research/RBPODO_EVALUATION.md`.

## Environment

Ubuntu 24.04, Python 3.12, NumPy; no rbpodo installation, controller, ROS, or robot.

## Method

Map zero, translation, axis, combined, and ±90° pitch poses through the generic
mapping twice; compare translation and rotation matrices; inject a NaN.

## Evidence class

`SOURCE_VERIFIED` convention plus `MOCK_VERIFIED` implementation. Not live evidence.

## Metrics

Maximum translation round-trip error, rotation-matrix equivalence, invalid rejection.

## Results

All eight cases and all acceptance gates passed in `results/metrics.json`.

## Limitations

No controller serialization, firmware variant, kinematics, or physical pose was measured.

## Conclusion

The isolated mapping is deterministic under the documented convention.

## Decision

`PROMOTE_TO_PLATFORM`
