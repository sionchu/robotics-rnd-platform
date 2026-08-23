# Vision Lab

Run the deterministic, hardware-free integration after an editable install:

```bash
python -m applications.vision_lab.mock_guidance
```

It transforms one camera-frame mock target into the robot-base frame, executes a
generic linear command against `MockRobot`, and reports a completed job. It is an
architecture smoke test, not perception or robot validation.
