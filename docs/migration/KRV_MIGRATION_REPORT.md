# KRV Migration Report

Date: 2026-08-23. This report follows the evidence/classifications in
`KRV_MIGRATION_INVENTORY.md`.

No original KRV code, tests, fixtures, configuration, data, binaries, or Git
history was copied. Every implementation below was written fresh with neutral
names from public mathematical definitions and the new platform requirements.

| Original concept | Why generic | Original code copied | New implementation | Semantic differences | New tests | Validation |
|---|---|---|---|---|---|---|
| Pose, transform, explicit frame direction | Rigid-body geometry is common to robotics | No | `core/frames.py`, `core/geometry/` | Value objects use meters, validated `FrameId`, normalized XYZW quaternions, framed points/poses, no SciPy dependency | `tests/unit/test_geometry.py` | 6 geometry tests pass; identity/inverse/composition/point/pose/invalid/frame guards covered |
| Typed result/quality/diagnostic values | Stable typed boundaries reduce adapter leakage | No | `core/models.py`, `core/diagnostics.py`, `robot/results.py` | Smaller neutral models; immutable mappings; timezone-aware timestamps | `test_config_and_models.py`, robot/vision contract tests | Python suite passes |
| Robot interface and deterministic simulator pattern | Hardware-independent control contracts enable mock-first testing | No | `robot/`, `drivers/mock/robot.py` | Capability-oriented command/result API; deterministic target state only, no physics; explicit fault/stop/reset | `test_robot_contract.py`, adapter tests | Connect/disconnect, disconnected command, joints, pose, stop, fault, reset, and invalid inputs pass |
| Vision result and replay pattern | Offline deterministic results are reusable across algorithms and hardware | No | `vision/`, `drivers/mock/vision.py`, `drivers/replay/vision.py` | Typed pose targets/quality rather than vendor capture arrays or KRV capture layouts; in-memory cursor/reset | `test_vision_contract.py` | Determinism, order, exhaustion, reset, frame metadata, and invalid data pass |
| Explicit lifecycle state | Jobs need testable transitions independent of UI/hardware | No | `core/state_machine.py` | Generic transition engine and neutral job lifecycle rather than camera service state | `test_state_machine.py` | Valid, invalid, stop, fault, and recovery paths pass |
| Interface-only guidance flow | Reusable behavior should compose robot, vision, and frames | No | `skills/robot_guidance/workflow.py`, mock Vision Lab | One-shot architecture proof only; no path planning, retry, production safety, or hardware claim | `tests/integration/test_mock_guidance.py` | Module smoke test completes and target transform is asserted |
| Configuration/path validation lesson | Reproducible config and explicit validation are broadly useful | No | `core/config.py`, bootstrap and doctor scripts | Standard-library TOML for core; no KRV YAML schemas or values | `test_config_and_models.py`, bootstrap dry run | Config validation passes; bootstrap preview and doctor run successfully |
| Calibration and registration result boundaries | Algorithms need neutral transform/quality outputs | No | `vision/calibration/`, `vision/registration/` | Models/contracts only; no vendor solver, board enum, session format, or unvalidated algorithm | Constructor validation plus architecture gates; future algorithms need dedicated tests | Imports/type/lint pass; no calibration accuracy claim |

## Intentionally not migrated

- KRV GUI/operator workflow, product/job/teaching schemas, and business sequencing;
- KRV TCP commands, messages, caching, or server behavior;
- direct camera implementation, official SDK adapter details, and hand-eye mapping;
- calibration observations/results, captures, point clouds, images, logs, datasets,
  operational configuration, device/network identifiers, and production values;
- existing test fixtures and all source/Git history.

The new Rainbow, Mech-Eye, and Mech-Vision files are explicit unavailable
skeletons, not migrated implementations. They publish no capabilities until a
separate official-documentation and hardware validation effort supplies evidence.

## Verification summary

- KRV snapshot read-only suite: `20 passed, 1 skipped`; non-generated source hash
  unchanged before/after.
- New platform: `27 passed`; Ruff lint/format clean; mypy clean; C++ build clean;
  CTest `1/1` passed; mock application completed; architecture import gates passed.
- No KRV hardware, RB robot, Mech-Eye camera, ROS graph, CUDA, or Isaac validation
  is claimed by this migration.
