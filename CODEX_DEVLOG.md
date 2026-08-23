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

## 2026-08-23 — v0.2 vision foundation research cycle

### Execution context and baseline

- Read the complete 1,571-line v0.2 Vision Foundation master prompt before making changes.
- Re-read the v0.1 source-of-truth set, including governance, architecture, roadmap, research workflow, security/IP rules, migration evidence, environment tooling, package metadata, source, and tests.
- Started from clean `main` at `4f17763`, with private remote `sionchu/robotics-rnd-platform`, tag `v0.1.0-bootstrap`, and no divergence from the remote.
- Preserved the v0.1 repository boundary and core dependency rule. No KAI, vendor, customer, credential, hardware-identity, private-network, dataset, or proprietary SDK artifact was introduced.

### NVIDIA/GPU checkpoint

- Identified an NVIDIA GeForce RTX 5060 Laptop GPU on PCI, with the `nvidia` driver bound, NVIDIA 580.95.05 kernel modules loaded, matching DKMS state for kernel `6.8.0-31-generic`, and Secure Boot disabled.
- Confirmed NVIDIA user-space driver libraries are installed. `nvcc` is absent, which is a CUDA Toolkit finding and is kept distinct from driver health.
- Found that this Codex process has an isolated, user-owned `/dev` tmpfs without `/dev/nvidia*` or `/dev/dri`, even though PCI, kernel modules, and `/proc/driver/nvidia` expose the GPU. Consequently, `nvidia-smi` cannot establish native-host operability from this sandbox.
- Classified the result as `GPU_UNKNOWN_REQUIRES_MANUAL_INTERVENTION` and recorded exact read-only host verification commands in `docs/setup/NVIDIA_GPU_STATUS.md`. No driver, CUDA, package, kernel, firmware, PRIME, or boot change was made, and no reboot was requested.
- Enhanced `scripts/doctor.py` so it separately reports GPU detection, kernel/device usability, `nvidia-smi`, the CUDA driver library, the CUDA Toolkit compiler, Docker, and ROS 2 without leaking unique GPU identifiers.

### Vision foundation implementation

- Added reusable camera models, distortion coefficients, image-source contracts, calibration observations/results, reprojection metrics, deterministic fixture sources, and human-readable calibration serialization.
- Added an OpenCV-backed camera calibration adapter and AprilTag detector while retaining OpenCV outside `robotics_rnd.core`; architecture tests enforce the boundary.
- Added generic AprilTag observations with documented TL/TR/BR/BL corner order, timestamps, frame/image metadata, and quality fields without leaking OpenCV objects through public models.
- Added planar-square PnP using IPPE Square with an iterative fallback for gross frontal degeneracy, explicit `T_camera_tag` semantics, reprojection helpers, pose-error metrics, and Rodrigues/transform conversion.
- Added a versioned benchmark schema and a CLI covering calibration, AprilTag detection, and PnP demonstration workflows.
- Used Python 3.12 and optional `opencv-python-headless` 4.14.0.94. No CUDA, ROS, or vendor dependency was added to the reusable vision foundation.

### Research cycle and decisions

- `001_camera_calibration`: 28 deterministic synthetic checkerboard views, 9×6 inner corners, 0.03 m square size, and 0.15 px corner noise. Estimated focal-length errors were 0.09495% (`fx`) and 0.09414% (`fy`); principal-point error was 0.510725 px; RMS/mean/max reprojection error was 0.205603/0.183197/0.593588 px. Decision: `PROMOTE_TO_PLATFORM`.
- `002_apriltag_detection`: AprilTag 36h11 fixtures covered baseline, scale, translation, rotation, perspective, blur, noise, and combined degradation. Detection and ID accuracy were 8/8, mean corner RMSE was 0.418508 px, and the latest uncontrolled CPU timing snapshot was 4.32634 ms/frame. Decision: `PROMOTE_TO_PLATFORM`.
- `003_apriltag_pnp_pose`: exact synthetic cases had maximum translation error `4.962419e-11` m, maximum orientation error 0 degrees, and maximum mean reprojection error `6.03653e-9` px. The raster detector-to-PnP case had 0.005047489 m translation error, 1.133312-degree orientation error, and 0.294247 px mean reprojection error. Decision: `PROMOTE_TO_PLATFORM`.
- `004_transform_chain`: 100 deterministic cases verified `T_base_tag = T_base_camera @ T_camera_tag`; maximum composition and inverse-recovery matrix errors were `8.326673e-16` and `8.881784e-16`. A reversed chain was rejected. Decision: `PROMOTE_TO_PLATFORM`.
- `005_pose_sensitivity`: 30 PnP trials per level plus 12 detection/PnP blur trials quantified distance, apparent tag size, tilt, corner noise, intrinsic error, and blur. At 1.6 m and about 66.9 px/tag edge, mean translation/orientation errors reached 9.419 mm/3.420 degrees; at 2 px corner noise they reached 9.651 mm/7.810 degrees; 2% intrinsic perturbation produced 18.484 mm/5.138 degrees while reprojection error remained 0.469 px; blur sigma 5 reduced detection success to 25%. Decision: `CONTINUE_RESEARCH`.
- Every experiment records its question, hypothesis, method, environment, data, metrics, results, failure cases, limitations, conclusion, and decision. All data are deterministic synthetic fixtures; no physical-camera or hardware-validity claim is made.

### Promotion and documentation

- Promoted only generic, tested components: camera/corner models, calibration and serialization, reprojection metrics, AprilTag observation/detection, PnP, pose metrics, transform validation, deterministic sources, benchmark schema, and CLI entry points.
- Added `docs/research/VISION_FOUNDATION_PROMOTION.md` with origin, evidence, responsibility, assumptions, limitations, and disposition for each candidate component.
- Added canonical camera/tag/frame/corner/PnP conventions and future integration guidance for Rainbow Robotics, Mech-Eye/Mech-Vision, Raspberry Pi, optional ROS 2, and NVIDIA acceleration.
- Updated the architecture, roadmap, learning roadmap, research workflow entry points, and official resources without treating implemented evidence as proof of personal mastery or hardware validation.

### Verification

- Python: `48 passed`.
- Research acceptance groups: calibration, AprilTag, PnP, transform chain, and sensitivity all passed in verify-only mode.
- Ruff lint: passed; Ruff format: 189 files already formatted.
- Mypy strict source check: `Success: no issues found in 69 source files`.
- C++ configure/build: passed; CTest: `1/1` passed.
- Environment doctor and deterministic mock guidance application: passed.
- Pre-commit, staged-diff/IP audit, final GitHub Actions state, push, and release-tag outcome are recorded by the final checkpoint commit and remote state after those gates complete.

### Commit checkpoints

- `dd004e3` — `docs: record NVIDIA GPU diagnosis`
- `40f2c07` — `feat(vision): add calibrated camera and pose foundation`
- `e2888eb` — `exp: add reproducible vision foundation studies`
- `8cfc1da` — `docs: connect vision foundation to future guidance`
- Final CI/devlog checkpoint: the commit containing this entry.

### Unresolved constraints and next evidence

- Native-host `nvidia-smi` must be run outside this sandbox before GPU operability or CUDA readiness can be claimed.
- The calibration, detection, pose, transform, and sensitivity evidence is synthetic. Lens behavior, exposure, motion blur, rolling shutter, print/target tolerances, focus, camera timing, and real device frames remain unmeasured.
- No live camera, physical AprilTag, robot, Mech-Eye, Mech-Vision, ROS graph, vendor SDK, or safety-critical motion was used.
- The next research cycle should validate the same acceptance metrics with a live camera and measured target before integrating robot motion or vendor-specific 3D vision.

## 2026-08-24 — Windows/WSL2 dual-workstation integration

### Repository and integration checkpoint

- Located the existing private GitHub repository created by the Ubuntu setup and
  used it as the only canonical remote.
- Cloned to `C:\dev` for Windows and to the WSL2 Linux filesystem; did not reuse
  the empty OneDrive working folder as a second repository.
- Created `win/bootstrap-desktop` from the then-current `main`. When Ubuntu
  advanced `main` to the v0.2 vision-foundation tag during the task, fetched it,
  rebased the Windows work, and resolved the CI, roadmap, package, CUDA resource,
  and architecture-test overlaps while preserving both sets of changes.
- Pushed only the task branch. `origin/main` was not rewritten or force-pushed.

### Windows and WSL2 platform work

- Added conservative Windows and WSL2 bootstrap/doctor scripts, example
  workstation profiles, cross-platform line-ending policy, data-root layout,
  storage/IP policy, sync guidance, capability matrix, and CI coverage.
- Added a bounded PyTorch CUDA matrix-multiply smoke experiment and a
  vendor-neutral OpenUSD robot/camera stage generator.
- Added Windows Isaac Sim readiness inspection with explicit RTX 4070 Ti memory
  constraints and no automatic Isaac, driver, or system CUDA installation.
- Added OpenUSD, PyTorch/CUDA, Isaac, and workstation learning/resource indexes.
- Expanded the core import boundary and made Ubuntu's synthetic NVIDIA doctor
  fixtures portable to Windows filesystems.
- Updated WSL GPU discovery to recognize the standard
  `/usr/lib/wsl/lib/nvidia-smi` location.

### Environment findings and installs

- Windows 11 desktop: Intel Core i5-13600KF, 31.85 GiB RAM, RTX 4070 Ti with
  12,282 MiB VRAM, NVIDIA driver 591.86, and driver CUDA ceiling 13.1.
- Windows tools used: Git 2.48.1, GitHub CLI 2.96.0, Visual Studio Build Tools
  2022/MSVC 19.44, CMake 4.1.1, Ninja 1.13.2, and Python 3.12.10.
- WSL2: Ubuntu 24.04.3, Python 3.12.3, GCC/G++ 13.3, CMake 3.28.3,
  Ninja 1.13.0, and Git 2.43.0.
- Created repository `.venv` environments and installed development, vision,
  OpenUSD 26.8, and PyTorch 2.12.1+cu130 dependencies. WSL packages remained
  user/repository scoped after non-interactive `sudo` was found unavailable.
- Did not install or change NVIDIA drivers, system CUDA Toolkit, Docker, Blender,
  ROS, vendor SDKs, firmware, security settings, or GitHub repository settings.

### Verification performed

- Windows Python suite: `49 passed in 1.75s`; WSL2 Python suite:
  `49 passed in 1.26s`.
- Ruff lint and format checks passed; Mypy reported no issues in 69 source files;
  every pre-commit hook passed on both Windows and WSL2.
- All five deterministic vision research acceptance groups passed in both
  environments.
- Windows MSVC C++ build and WSL2 GNU/Ninja C++ build passed; CTest was 1/1 in
  both environments.
- The deterministic mock guidance application completed on Windows with
  `hardware_validated: false`.
- Windows and WSL2 PyTorch CUDA smoke tests used the same 512×512 FP32 workload
  for 10 iterations on compute capability 8.9. Both produced checksum
  `7.302420616149902`, reported CUDA runtime 13.0, and passed.
- OpenUSD 26.8 created a generic robot/camera USDA stage with default primitive
  `/World`, meters-per-unit 1, and Z-up in the external Windows and WSL2 data
  roots.
- Isaac Sim 6.0.1 was already installed. Its packaged compatibility checker
  exited successfully, but the 12 GB-class GPU is below NVIDIA's published
  16 GB minimum and no scene workload was launched.

### Data, IP, and limitations

- Created external data-root directories for datasets, models, recordings, USD,
  synthetic outputs, benchmarks, exports, and caches. Generated reports and
  stages remain ignored and outside source control.
- No company repository, private dataset, model weight, recording, calibration,
  credential, device identifier, network address, vendor binary, or proprietary
  SDK source was committed.
- Physical cameras, robots, vendor cameras, ROS graphs, Isaac scenes, TensorRT,
  Docker, and `nvcc` builds remain outside this checkpoint.
- Next task: run an identical core/vision replay parity cycle at one commit on
  Ubuntu, Windows, and WSL2, then define the first vendor-neutral robot/camera USD
  replay mapping from those measured results.
