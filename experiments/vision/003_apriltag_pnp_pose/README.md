# Experiment 003 — AprilTag PnP Pose

Question: given calibrated intrinsics and a 120 mm tag, can the platform recover
`T_camera_tag` and preserve `T_target_source` semantics?

The default candidate generator is `SOLVEPNP_IPPE_SQUARE`, whose required
object-point order matches the detector's top-left, top-right, bottom-right,
bottom-left order. A gross-reprojection fallback uses `SOLVEPNP_ITERATIVE` for
the exactly front-facing planar degeneracy. The selected method is reported.

```bash
python -m experiments.vision.run_all pnp
```
