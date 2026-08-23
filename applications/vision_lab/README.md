# Vision Lab

Run the deterministic, hardware-free integration after an editable install:

```bash
python -m applications.vision_lab.mock_guidance
```

It transforms one camera-frame mock target into the robot-base frame, executes a
generic linear command against `MockRobot`, and reports a completed job. It is an
architecture smoke test, not perception or robot validation.

Run the v0.2 CPU-only perception research separately:

```bash
python -m robotics_rnd.vision calibration
python -m robotics_rnd.vision apriltag
python -m robotics_rnd.vision pnp
python -m experiments.vision.run_all all
```

These commands use synthetic/replay input and do not command a robot.
