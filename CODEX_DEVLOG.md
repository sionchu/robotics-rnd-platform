# Codex Development Log

## 2026-08-23 — v0.1 autonomous bootstrap

### Execution context

- Agent: Codex, GPT-5 family. Internal service configuration is not exposed to the repository.
- Goal: create a vendor-independent Robotics R&D Platform v0.1 after inspecting the available KAI Robotics Vision material, while preserving repository and intellectual-property boundaries.
- New repository: `robotics-rnd-platform`, initialized independently on branch `main`.
- Source repository handling: read-only inspection. No source files, configuration values, data, binaries, credentials, or Git objects were copied from KAI Robotics Vision.

### Source material inspected

- The complete 1,983-line master prompt.
- Three complete KAI Robotics Vision stage briefs supplied with the workspace.
- The available `nano_vision` KAI Robotics Vision snapshot: README, packaging metadata, Python source tree, tests, module imports, and public definitions.
- The requested KAI source-of-truth document names and Git metadata were searched for explicitly. `AGENTS.md`, `PROJECT_STATE.md`, `CODEX_DEVLOG.md`, `CODEX_HANDOFF.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `KNOWN_ISSUES.md`, `TEST_GAPS.md`, `AUDIT_REPORT.md`, and Git history were not present in the available snapshot.
- The outer workspace repository was inspected. Its Git metadata is read-only in this environment, so the platform was created as a distinct nested repository with the required name rather than modifying the outer repository.

### Migration and architecture decisions

- Recorded evidence and migrate/adapt/reject/defer decisions in `docs/migration/KRV_MIGRATION_INVENTORY.md`.
- Reimplemented only generic concepts from first principles: geometry, frames, robot and vision contracts, job/state models, replay, mocks, configuration, diagnostics, and quality metrics.
- Kept the core independent of ROS 2, OpenCV, vendor SDKs, CUDA, and hardware libraries. Architecture tests enforce those import boundaries.
- Defined transforms as `T_target_source`, translation in metres, robot joints in radians, and quaternions in normalized XYZW order.
- Added safe unavailable drivers for Rainbow Robotics and separate Mech-Eye acquisition and Mech-Vision processing interfaces. They do not import unavailable SDKs or claim hardware validation.
- Used Python 3.12 for orchestration and interfaces, plus an independent C++17 geometry smoke target for future performance-sensitive work.
- Kept datasets, models, captures, bags, credentials, binaries, and vendor SDK artifacts out of Git.

### Implementation grouped by area

- Governance and IP: `README.md`, `AGENTS.md`, `SECURITY_AND_IP.md`, `ARCHITECTURE.md`, ADR 0001, migration inventory, and migration report.
- Core: frames, geometry, transforms, quality, tasks/jobs, state machine, diagnostics, TOML configuration, and structured logging.
- Robotics: generic robot contract, command/result/state models, deterministic mock robot, and safe Rainbow driver placeholder.
- Vision: generic vision contract, observations, calibration and registration models, deterministic mock/replay providers, and separate Mech-Eye/Mech-Vision placeholders.
- Skills and applications: a generic mock guidance job and executable vision-lab example.
- Research operations: roadmap, workflow, use cases, Ubuntu setup, learning roadmap, hardware plans, official resource indexes, and an experiment template.
- Tooling: `pyproject.toml`, pre-commit hooks, GitHub Actions, environment doctor, conservative bootstrap script, experiment generator, and aggregate test script.
- C++: CMake project, vector implementation, example, and CTest smoke test.

### Commands and verification performed

- KAI snapshot regression check using its preserved Python 3.11 environment: `20 passed, 1 skipped in 1.43s`.
- KAI non-generated file digest before and after inspection/testing: `1ad6314084317a071fac0018ecef9ccc6c3bc9e78303d0b81e422fb7cac836b7` (unchanged).
- New platform Python suite: `27 passed`.
- Ruff lint and format checks: passed.
- Mypy strict source check: `Success: no issues found in 51 source files`.
- C++ configure/build: passed with CMake 3.28.3, Ninja 1.11.1, and GNU C++ 13.2.0.
- CTest: `1/1` passed.
- Pre-commit: every configured hook passed using a temporary writable cache.
- Initial remote GitHub Actions run: Python and C++ jobs passed. Its deprecated
  action-runtime warnings were then removed by pinning the current official
  Checkout v7.0.1 and Setup Python v7.0.0 release commit SHAs.
- Mock guidance application: reached `COMPLETED`, produced deterministic command `mock-0001`, and reported `hardware_validated: false`.
- Bootstrap dry run: passed without installing ROS, CUDA, or vendor software.
- Repository audit: no tracked binaries, no tracked file over 1 MiB, no detected credential/private-key/serial/IP patterns, and no vendor or KAI source artifacts.

### Environment findings

- Ubuntu 24.04 LTS, x86_64.
- AMD Ryzen AI 7 350, 8 physical cores / 16 logical CPUs, approximately 30 GiB RAM, no swap.
- Python 3.12.3, Git 2.43.0, CMake 3.28.3, Ninja 1.11.1, and GNU C++ 13.2.0.
- ROS 2 Jazzy is installed at `/opt/ros/jazzy` and works after sourcing its setup script; it is intentionally optional and not sourced globally by this repository.
- The NVIDIA driver is not communicating and `nvcc` is absent, so no GPU/CUDA capability is claimed.
- Docker is absent.
- GitHub CLI authentication was available. The destination remote was created empty and verified `PRIVATE`; final push and bootstrap tag are performed only after the final commit candidate passes all gates.

### Commit checkpoints

- `c04e4e8` — `docs: define migration and IP boundaries`
- `0c63c4e` — `feat(platform): add generic contracts mocks and tests`
- `c8bfd59` — `feat(research): add workflows hardware plans and resources`
- Final verification/devlog checkpoint: the commit containing this entry.
- CI hardening checkpoint: the commit containing the SHA-pinned current action releases.

### Unresolved constraints and risks

- No KAI Git history or requested source-of-truth documents were available; migration provenance is therefore limited to the supplied snapshot and stage briefs.
- Rainbow, Mech-Eye, Mech-Vision, ROS 2 integration, and NVIDIA acceleration remain unvalidated on hardware.
- No physical devices, vendor SDKs, private datasets, calibration artifacts, or model weights were available or introduced.
- GPU and CUDA installation should not proceed until the workstation's NVIDIA hardware and driver state are resolved deliberately.
