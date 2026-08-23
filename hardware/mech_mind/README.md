# Mech-Mind Research Boundaries

Two integrations must remain distinct:

```text
Mech-Eye -> official SDK -> MechEyeDriver -> images/depth/cloud -> our skills
Application -> VisionInterface -> MechVisionProvider -> supported Standard Interface
```

The direct path owns acquisition and lets platform experiments own calibration,
features, pose, registration, refinement, inspection, or guidance. The provider
path consumes results from an external vision project. Neither SDK/protocol is a
core dependency.

Bootstrap includes safe stubs only. Future work must select then-current official
documentation, isolate SDK installation, translate to platform models, add
hardware-gated contract tests, and retain mock/replay substitutes. Never commit
SDK files, network/device identifiers, private captures, or calibration results.
