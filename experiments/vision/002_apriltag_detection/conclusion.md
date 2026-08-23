# Conclusion

## Question

Can the platform detect a known AprilTag deterministically and return a neutral
observation?

## Hypothesis

Exactly tag id 7 will be recovered in all eight synthetic scenarios.

## Method

Rendered `tag36h11` through known projective camera geometry, added controlled
scale, translation, rotation, perspective, blur, and noise, then detected with
OpenCV 4.14.0 `ArucoDetector`.

## Environment

Ubuntu 24.04, Python 3.12.3, CPU OpenCV 4.14.0; no physical camera or GPU.

## Data

Eight seed-controlled generated images; six compact PNG fixtures are retained.

## Metrics

Detection/id success rate, ideal-corner RMSE, latency, and generic quad quality.

## Results

All eight tags were detected with the correct id. Mean corner RMSE was 0.41851
px. Output contained only platform values, not OpenCV detector objects.

## Failure cases

No-tag input returns an empty tuple. Unknown families and invalid clockwise
corner geometry are rejected. Partial occlusion was not accepted as a gate.

## Limitations

Synthetic rasterization is cleaner than physical optics. Decision margin is not
available from this OpenCV API, so neutral perimeter and area metrics are used.

## Conclusion

The detector provides deterministic, replayable, library-contained AprilTag
observations suitable for the PnP boundary.

## Decision

`PROMOTE_TO_PLATFORM`
