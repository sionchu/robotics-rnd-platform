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

`create_stage.py` validates a generic JSON or YAML Workcell Exchange manifest,
resolves its transform graph through `robotics_rnd.core`, and creates an OpenUSD
stage using only `pxr` APIs. It sets `metersPerUnit = 1`, Z-up, `/World` as the
default prim, and emits `/Robot`, `/Camera`, `/Fixture`, `/Target`, and
`/Robot/Tool` with platform-owned frame metadata.

```bash
python experiments/openusd/create_stage.py \
  --manifest config/workcells/minimal-workcell.yaml \
  --schema schemas/workcell-exchange-v1.schema.json \
  --output reports/local/openusd/minimal-workcell.usda
```

The generator contains no geometry, manufacturing behavior, physics, Isaac,
ROS, CUDA, or vendor SDK integration. The stage is an interchange fixture, not a
simulation result.

Generated stages default to ignored `reports/local/openusd/`.
