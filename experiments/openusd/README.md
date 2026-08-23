# Generic OpenUSD Stage Experiment

```yaml
platforms:
  ubuntu: supported
  windows: supported
  wsl: supported
requires:
  gpu: false
  ros2: false
  hardware: none
  python_package: pxr
```

`create_stage.py` creates a small generic robot base and camera rig using only
OpenUSD `pxr` APIs. It sets `metersPerUnit = 1`, Z-up, a stable `/World` hierarchy,
and platform-owned role metadata. It does not import Isaac, ROS, CUDA, or vendor
SDKs and uses no company asset.

Generated stages default to ignored `reports/local/openusd/`.
