# Camera Controls and Timing

## Canonical stream

The initial analysis format is `BGR888` at one explicitly selected resolution.
This feeds OpenCV without a repeated RGB-to-BGR conversion. `RGB888` is exposed
only when a caller explicitly selects it. The selected Picamera2 mode, sensor
output, stored resolution, and algorithm resolution must all be recorded.

No custom `ScalerCrop` is accepted as an implicit calibration match. If a crop
is present in capture metadata, bind it to a separate calibration artifact.

## Auto baseline

Auto mode requests `AeEnable` and `AwbEnable` where the detected camera stack
advertises them. Capture at least 20 warm-up frames, then retain exposure,
analogue/digital gain, colour gains, frame duration, lens position when
available, and focus figure-of-merit as metadata.

Auto mode is useful for bring-up but can introduce frame-to-frame variation.

## Controlled measurements

After inspecting a stable auto sequence, rerun with supported explicit values:

```bash
python3 -m robotics_rnd.edge capture \
  --output datasets/local/pi_camera/<new-session-id> \
  --camera-mode '<exact detected mode label>' \
  --frames 200 \
  --exposure-time-us <observed-value> \
  --analogue-gain <observed-value> \
  --colour-gains <red> <blue>
```

Specify `--lens-position` only if `rpicam-hello --list-cameras`/Picamera2
capability discovery shows a supported focus control. A fixed-focus camera must
not be treated as autofocus-capable. Unsupported controls fail before capture.

## Timestamp meanings

- `SensorTimestamp`: sensor/camera-stack timestamp when Picamera2 provides it.
- `monotonic_timestamp_ns`: Pi monotonic time immediately after a captured
  request is received; used for frame intervals within one boot.
- `captured_at`: timezone-aware UTC receive/write orchestration time.
- processing start/end: measured separately during replay/benchmark.
- filesystem modification time: never treated as capture time.

Sensor and monotonic clocks have different epochs. No synchronization between
the Pi and laptop is claimed in v0.2.1.
