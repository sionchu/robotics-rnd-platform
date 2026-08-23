# Raspberry Pi Camera Edge Node

This directory defines the Raspberry Pi 4 camera node as an optional hardware
adapter for the generic `ImageSource` pipeline. It contains no detected device
record because `pi-rnd` was unreachable during v0.2.1 preparation.

Current milestone state: `PREPARATION_COMPLETE_HARDWARE_VALIDATION_PENDING`.
Physical experiment state: `NOT_RUN_HARDWARE_UNAVAILABLE`.

The expected path is:

```text
Picamera2 -> PiCameraSource -> ImageFrame + CaptureMetadata
           -> AprilTag -> PnP -> T_camera_tag -> metrics/results
```

Picamera2 and libcamera remain adapter dependencies. They are imported lazily
and are never required by the core, normal tests, laptop replay, or CI.

Directory contents:

- `SETUP.md`: current-system-first inspection and safe OS/package guidance.
- `CAMERA_CONTROLS.md`: auto/controlled capture and timestamp semantics.
- `DEPLOYMENT.md`: wheel deployment, capture, transfer, and replay commands.
- `schemas/`: sanitized hardware and capture schemas.
- `deployment-manifest.json`: minimal deployable contents and version policy.

Raw data belongs under ignored `datasets/local/pi_camera/<session-id>/`, never
under this hardware documentation directory.
