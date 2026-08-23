# Experiment 006 — Pi Camera Bring-up

Question: can the detected Raspberry Pi camera capture reproducible frames and
metadata through `PiCameraSource` without leaking Picamera2 into generic APIs?

Run the Pi doctor, select an actual reported mode, then capture an auto-control
and controlled sequence using the commands in
`docs/research/PI_CAMERA_HARDWARE_HANDOFF.md`. Record capture success, frame
intervals, exposure/gain behavior, CPU/memory, and software versions.

Current state: `NOT_RUN_HARDWARE_UNAVAILABLE`.
