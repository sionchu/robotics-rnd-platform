# KRV Migration Inventory

Status: completed from read-only evidence on 2026-08-23.

## Evidence and limits

The only discoverable KAI Robotics Vision candidate was an external `nano_vision`
working snapshot. It is not a Git repository. It contains a README, packaging
metadata, source, tests, local configuration, generated data, and three prior
Codex stage briefs, but no `AGENTS.md`, `PROJECT_STATE.md`, `CODEX_DEVLOG.md`,
`CODEX_HANDOFF.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `KNOWN_ISSUES.md`,
`TEST_GAPS.md`, or `AUDIT_REPORT.md`. Consequently, commit history and authorial
provenance could not be reviewed.

The inspection covered the README, packaging metadata, all source and test file
names, the generic geometry/robot/replay/config/job/safety/communication modules,
the calibration and camera boundaries, service composition, test bodies, and all
three prior stage briefs. A read-only software test run reported `20 passed, 1
skipped`; a hash of non-generated project files was identical before and after.
No hardware tests were requested or run.

This inventory records engineering evidence; it is not permission to copy code
and is not a legal ownership determination. No source, history, configuration,
capture, dataset, device identifier, network value, or vendor binary was copied.

## Classification inventory

| Source area/file | Concept | Current responsibility | Dependencies | Classification | Reason | Proposed destination | Migration method | Verification method | IP/sensitivity note |
|---|---|---|---|---|---|---|---|---|---|
| `geometry/pose.py`, `geometry/transform.py` | Pose and rigid transform | Validates vectors/quaternions and composes frame-labelled transforms | NumPy, SciPy | REIMPLEMENT-GENERIC | Rigid-body math is generic, but implementation provenance is not established | `robotics_rnd/core/geometry/` | Fresh implementation from mathematical definitions; different data model and no SciPy public boundary | Independent identity, inverse, composition, point, and pose tests | No original code or test vectors copied |
| `geometry/frames.py` | Coordinate-frame naming | Names frames and states transform direction | Python constants | ADAPT-CONCEPT | Explicit source/target direction is a reusable design lesson | `robotics_rnd/core/frames.py`, `ARCHITECTURE.md` | Define a validated neutral `FrameId` and document `T_target_source` | Frame mismatch and convention tests | Application frame names are not migrated as a fixed global list |
| `geometry/conversions.py` and README | Explicit units | Converts UI/hardware boundary units | NumPy | REIMPLEMENT-GENERIC | Explicit SI boundaries are broadly reusable | Geometry and robot models | Fresh scalar/value-object design with meters, radians, seconds, and XYZW documented | Unit/convention guard tests | Hardware-native unit claims remain in the original project |
| `robot/protocol_types.py`, `replay/source.py`, calibration and measurement dataclasses | Data models | Carries robot, capture, calibration, and measurement state | NumPy, application schemas | ADAPT-CONCEPT | Typed immutable values are useful; the existing schemas encode application concerns | `core/models.py`, `robot/models.py`, `vision/models.py` | Design new minimal neutral models from platform requirements | Constructor validation and contract tests | Device/capture metadata and product schemas are excluded |
| `config/loader.py`, `config/paths.py` | Configuration loading and paths | YAML persistence and user/development paths | PyYAML, filesystem | REIMPLEMENT-GENERIC | Validation and path separation are generic | `core/config.py` | Fresh TOML read/validation using the standard library | Valid, missing, and invalid configuration tests | Existing YAML files and values are DO-NOT-MIGRATE |
| `application.py` | Logging composition | Configures stream/file logging at the composition root | Python logging | ADAPT-CONCEPT | Centralized configuration is reusable; application composition is not | `core/logging.py` | Fresh idempotent configuration helper | Smoke test and example log output | Existing log files are DO-NOT-MIGRATE |
| `camera.py`, diagnostics page, `CameraService.status()` | Diagnostics | Reports actionable state and read-only environment details | OS commands, vendor facade, GUI | ADAPT-CONCEPT | Structured status with human remediation is reusable | `core/diagnostics.py`, `scripts/doctor.py` | Define neutral severity/status records and independent workstation detection | Doctor smoke test and diagnostic model tests | Network topology and device identifiers are DO-NOT-MIGRATE |
| `CameraOperationState` and prior stage briefs | State machines | Enumerates camera lifecycle; no reusable transition engine exists | Camera service | ADAPT-CONCEPT | Explicit transitions are a useful lesson, but the implementation is service-specific | `core/state_machine.py` | Fresh generic transition engine and job lifecycle | Valid/invalid/fault/recovery tests | Camera ownership and GUI behavior remain in KRV |
| `robot/base.py`, simulator, protocol types | Robot state/command abstraction | Defines application robot adapter and safe simulator | Geometry and application target schema | REIMPLEMENT-GENERIC | Interface-first robot control and deterministic mocks are generic | `robot/`, `drivers/mock/robot.py` | New capability-oriented interface, commands, results, errors, and mock | Shared robot contract tests | Existing target/job semantics and future RB assumptions are not copied |
| `replay/CaptureData`, `CameraCaptureResult` | Vision result abstraction | Carries image/depth/cloud capture results | NumPy, OpenCV, Open3D, vendor metadata | REIMPLEMENT-GENERIC | Timestamp/frame/pose/quality are generic requirements | `vision/models.py` | New vendor-neutral observation and target records | Determinism, metadata, invalid-data tests | Images, clouds, capture paths, and camera metadata are excluded |
| `calibration/solver.py`, observation/session modules | Calibration math and workflow | Persists observations and calls a vendor hand-eye solver | Vendor SDK, OpenCV, NumPy, SciPy | ADAPT-CONCEPT | Calibration result/quality boundaries are generic; solver and workflow are vendor/application specific | `vision/calibration/` | Define only neutral result contracts now; future algorithms require independent references | Model validation tests; no hardware claim | Solver adapter, board types, observations, and device data stay in KRV |
| No implemented generic registration module; future notes in briefs | Registration/refinement abstractions | Discussed as future perception work | Not implemented | COPY-NONE | There is no implementation evidence to migrate | Future `vision/registration/` contract | Create a neutral placeholder only when an experiment justifies it | Future contract/algorithm tests | Do not infer proprietary CAD or fitting requirements |
| `replay/source.py`, `recorded_source.py`, replay tests | Replay/simulator pattern | Separates live and recorded acquisition | NumPy, OpenCV, Open3D, capture layout | REIMPLEMENT-GENERIC | Deterministic offline replay is a broadly useful testing pattern | `drivers/replay/vision.py` | Fresh in-memory typed replay, independent of KRV file formats | Cursor, exhaustion, reset, and ordering tests | No capture files, layouts, or metadata copied |
| `tests/**` | Test fixtures and regression gates | Exercises geometry, GUI, SDK surface, jobs, replay, safety, TCP | Project code and vendor environment | COPY-NONE | Existing fixtures encode the original application and provenance is unclear | `tests/` | Write new generic fixtures and expected values | New suite must pass independently | No fixture, sample, device detail, or test code copied |
| `communication/protocol.py`, `vision_server.py` | Protocol framing | Implements an application JSON-lines command server | Sockets and service composition | KEEP-IN-KRV | Command names, caching, payloads, and capture semantics are application-specific | None in platform core; future `integrations/tcp/` | Document an integration boundary only | Architecture import checks | Internal protocol details must not enter the personal platform |
| `jobs/model.py`, repository, GUI | Job/task concepts | Persists product-oriented ROI, perception, grasp, and teaching schemas | YAML and UI | KEEP-IN-KRV | The current schema is application workflow, not a universal robotics job | Neutral `Task`/`Job` lifecycle only | Independently define IDs, state, and timestamps without recipe fields | State-machine and model tests | Product recipes and taught targets are sensitive/application-specific |
| `measurement/tools.py`, teaching GUI and briefs | Feature/measurement concepts | Point, ROI, distance, plane, and teaching workflow | NumPy, GUI, capture correspondence | ADAPT-CONCEPT | Quality/measurement result concepts are generic, while workflows and data are application-specific | `core/models.py`, future skills/experiments | Add neutral `QualityMetric`; re-evaluate algorithms through independent experiments | Model tests and future benchmark evidence | No production geometry, captures, or taught target data migrated |
| `safety/validator.py`, camera/robot exceptions | Error/result models | Returns structured safety issues and operational errors | Robot/application models | REIMPLEMENT-GENERIC | Explicit typed errors/results improve every adapter boundary | `robot/results.py`, `robot/errors.py`, `core/diagnostics.py` | Fresh success/error/status vocabulary | Failure-path and validation tests | Original error strings and business gates are not copied |
| `camera.py`, `services/camera_service.py` | Direct Mech-Eye integration | Discovers, connects, captures, and persists vendor data | Mech-Eye SDK, OpenCV, Open3D | DO-NOT-MIGRATE | Vendor-specific implementation and device metadata belong behind a dedicated adapter and may have license/IP constraints | Skeleton at `drivers/mech_eye/` only | Write a safe unavailable adapter without SDK code | Stub failure tests and architecture checks | No SDK imports, binaries, samples, identifiers, or captures copied |
| `calibration/solver.py` | Vendor hand-eye adapter | Maps vendor API and board enums to application results | Mech-Eye SDK | DO-NOT-MIGRATE | It is explicitly vendor/version-specific | Future `drivers/mech_eye/` extension | Rebuild only from then-current official documentation when needed | Hardware-gated adapter tests | SDK names and behavior are not platform-core contracts |
| `ui/**` | Desktop HMI behavior | Operator/engineer GUI, live capture, measurement, teaching | PySide6, OpenCV, vendor services | KEEP-IN-KRV | UI workflow is the existing application, not reusable platform core | Future independent application in `integrations/gui/` | Consume released platform contracts later | Application-level acceptance tests | Screenshots, labels, and process behavior are not migrated |
| `config/**`, `data/**`, logs, generated metadata | Operational assets | Stores network/device settings, captures, calibration, jobs, logs | Local hardware and process context | DO-NOT-MIGRATE | High likelihood of identifiers, topology, proprietary data, or large artifacts | None | Exclude and add preventive ignore/security rules | Secret/IP scan and tracked-file review | Treat as sensitive even when individual files look harmless |

## Evidence-backed conclusion

The safe reusable lessons are explicit units and frame direction, typed boundary
models, adapter isolation, deterministic mock/replay behavior, structured
results, and testable lifecycle transitions. They will be implemented from
scratch with neutral names and new tests. The original application, UI,
protocol, recipes, operational data, hardware configuration, vendor SDK code,
calibration adapter, and repository history remain entirely separate.
