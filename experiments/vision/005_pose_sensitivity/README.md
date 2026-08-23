# Experiment 005 — AprilTag Pose Sensitivity

Question: how do distance/tag pixel size, view angle, corner noise, calibration
bias, and blur affect AprilTag pose accuracy?

The study uses a manageable one-factor-at-a-time design: 30 seeded mathematical
PnP trials per level plus 12 rendered detection/PnP trials per blur level. It is
not a physical uncertainty model.

```bash
python -m experiments.vision.run_all sensitivity
```
