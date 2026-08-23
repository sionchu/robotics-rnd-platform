# Handoff

## Objective

Finalize the Windows/WSL2 bootstrap branch with a vendor-neutral Workcell
Exchange Schema and manifest-driven OpenUSD workcell while preserving the
canonical Ubuntu history and company/private-data boundaries.

## Scope

- Inspect Windows, WSL2, GPU, Git, GitHub authentication, and the existing Isaac
  Sim installation.
- Synchronize with the canonical private GitHub repository through a Windows
  task branch.
- Add cross-platform bootstrap, diagnostics, workstation profiles, CI, GPU smoke
  tests, an OpenUSD baseline, data/IP policies, and operator documentation.
- Validate the portable Python/C++/vision baseline on Windows and WSL2.
- Define world, robot-base, tool, camera, fixture, and target frames in metres,
  radians, normalized XYZW quaternions, and `T_target_source` direction.
- Generate and reopen a minimal OpenUSD workcell from equivalent JSON/YAML
  manifests without adding manufacturing simulation behavior.
- Prepare `win/bootstrap-desktop` for review into `main`.

## Acceptance criteria

- Preserve `origin/main` and integrate all Ubuntu work that advanced during the
  task.
- Keep host data, models, recordings, generated USD, benchmarks, vendor SDKs,
  credentials, and company IP outside Git.
- Demonstrate bounded CUDA execution on the RTX 4070 Ti in Windows and WSL2.
- Produce a vendor-neutral OpenUSD artifact outside Git.
- Run relevant local quality gates, commit the work, push only the task branch,
  and leave an evidence-backed continuation point.
- Validate schema shape, semantic transform graphs, JSON round trip, OpenUSD
  mapping, and architecture separation on Windows, WSL2, and CI.

## Completed

- Located the private canonical remote and cloned it to `C:\dev` and the WSL2
  Linux filesystem.
- Created and pushed `win/bootstrap-desktop`; rebased it onto Ubuntu's newer
  v0.2 vision-foundation `main` without force-pushing.
- Added Windows/WSL2 bootstrap and doctor tooling, workstation profiles,
  dual-platform CI, data/IP boundaries, GPU smoke benchmarking, OpenUSD stage
  generation, capability documentation, and Isaac readiness checks.
- Integrated Ubuntu's newer vision implementation and cross-platform-hardened
  its synthetic NVIDIA diagnostic tests.
- Installed only repository-scoped or user-scoped development dependencies.
  No driver, system CUDA Toolkit, Docker, vendor SDK, or security setting was
  changed.
- Added Workcell Exchange Schema 1.0, equivalent generic JSON/YAML manifests,
  core-backed transform resolution, and a manifest-driven metric OpenUSD stage.
- Added schema, semantic, round-trip, OpenUSD reopen, and architecture tests.
- Documented consumption/production boundaries for the future
  `manufacturing-digital-twin-rnd` repository.

## Current checkpoint

- Branch: `win/bootstrap-desktop`
- Base: `origin/main` at `c01e9a1`
- Validated schema implementation baseline: `2506f3b`
- Windows and the separate WSL2 Linux-filesystem clone are on the same task
  branch. The branch is ready for final documentation, CI, and PR review.

## Decisions and reasons

- Used task-branch integration because Ubuntu advanced `main` during Windows
  work; this preserves both histories and keeps review/merge explicit.
- Used PyTorch's CUDA runtime rather than installing a system CUDA Toolkit,
  because the smoke workload does not need `nvcc` and avoids broad host changes.
- Kept Isaac Sim optional because 12 GB VRAM is below the published 16 GB
  minimum; a successful compatibility checker is not treated as a scene result.
- Kept all generated GPU reports and USD stages in external data roots because
  they are runtime artifacts, not source.
- Retained vendor adapters as placeholders and did not copy vendor/company source
  or private captures into the platform.
- Kept `robotics_rnd.exchange` separate from core and OpenUSD. The exchange
  package depends on core transforms plus optional JSON Schema/YAML libraries;
  only the experiment adapter imports `pxr`.
- Required a connected parent/child transform tree and used core composition to
  resolve all `T_target_source` queries instead of defining another math stack.
- Kept the USD example to empty transform/camera prims, because geometry,
  physics, processes, and manufacturing simulation belong in a future separate
  repository.

## Verification evidence

- Windows Python: 56 passed; Ruff, formatting, Mypy (71 source files), and all
  pre-commit hooks passed.
- Windows C++: MSVC build passed; CTest 1/1 passed.
- Windows vision research: five acceptance groups passed.
- Windows GPU smoke: PyTorch 2.12.1+cu130, CUDA runtime 13.0, RTX 4070 Ti,
  compute capability 8.9, checksum 7.302420616149902, status PASS.
- WSL2 Python: 56 passed; Ruff, formatting, Mypy (71 source files), and all
  pre-commit hooks passed.
- WSL2 C++: GNU/Ninja build passed; CTest 1/1 passed.
- WSL2 vision research: five acceptance groups passed.
- WSL2 GPU smoke: PyTorch 2.12.1+cu130, CUDA runtime 13.0, RTX 4070 Ti,
  compute capability 8.9, checksum 7.302420616149902, status PASS.
- OpenUSD 26.8 created stages with `defaultPrim = World`, `metersPerUnit = 1`,
  and `upAxis = Z` on both Windows and WSL2.
- Both JSON and YAML manifests generated the required `/World`, `/Robot`,
  `/Camera`, `/Fixture`, and `/Target` prims; `/Robot/Tool` retains the tool
  frame. The generated stages reopened successfully.
- Schema tests reject unit changes, non-normalized XYZW quaternions, disconnected
  transform edges, and unknown frame queries.
- GitHub Actions run `32662640913` passed Python and C++ jobs on both
  `windows-latest` and `ubuntu-latest` for commit `2506f3b`.
- Isaac Sim 6.0.1 packaged compatibility checker exited successfully; the
  readiness assessment remains limited by 12,282 MiB VRAM.

## Not executed

- No physical camera, AprilTag target, robot, vendor camera, ROS graph, or
  safety-critical motion was used.
- No Isaac Sim scene, sensor, RTX-rendering, or sustained-memory workload was
  launched.
- No Docker workflow, TensorRT workflow, `nvcc` build, or vendor SDK install was
  performed.
- No Ubuntu laptop commands were issued from the Windows task.
- No merge to `main`, release tag, or force-push was performed.
- No Blender, Docker, CUDA Toolkit, Isaac feature, geometry asset, physics,
  process model, or manufacturing simulation code was added.

## Blockers

- Isaac Sim scene validation requires a deliberately bounded workload and may
  still be constrained by VRAM below the official minimum.
- Ubuntu laptop GPU operability still requires its documented native-host test.
- Hardware and vendor integration require authorized devices, SDKs, safety
  review, and appropriately separated data.
- No blocker remains for opening a PR from `win/bootstrap-desktop` after the
  final GitHub Actions result is green.

## Modified files

- Workstation/CI/config: `.github/workflows/quality.yml`, `.gitattributes`,
  `.gitignore`, `.editorconfig`, `pyproject.toml`, `config/workstations/`.
- Runtime tools: `scripts/common/`, `scripts/windows/`, `scripts/wsl/`,
  `experiments/gpu/`, `experiments/openusd/`.
- Policy/docs: `docs/data/`, `docs/workstations/`, `docs/digital_twin/`,
  `docs/learning/openusd/`, `resources/openusd/`, `resources/rtx4070ti/`, plus
  updates to root architecture, roadmap, resource, and project documents.
- Tests: cross-platform workstation configuration and architecture/diagnostic
  boundary updates.
- Workcell exchange: `schemas/workcell-exchange-v1.schema.json`,
  `config/workcells/`, `src/robotics_rnd/exchange/`,
  `experiments/openusd/create_stage.py`, and the new architecture/integration/
  unit tests.

## Next concrete action

Open a PR from `win/bootstrap-desktop` into `main`, review the schema contract and
CI matrix, and merge through the normal GitHub workflow. After merge, pin that
commit in the future `manufacturing-digital-twin-rnd` repository and add its
first consumer-side contract test before any manufacturing-domain extension.
