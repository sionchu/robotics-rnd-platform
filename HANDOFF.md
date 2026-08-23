# Handoff

## Objective

Extend the canonical Ubuntu-created `robotics-rnd-platform` repository into a
safe dual-workstation Windows/WSL2 robotics R&D platform without duplicating the
repository, overwriting newer Ubuntu work, or mixing company/private data into
Git.

## Scope

- Inspect Windows, WSL2, GPU, Git, GitHub authentication, and the existing Isaac
  Sim installation.
- Synchronize with the canonical private GitHub repository through a Windows
  task branch.
- Add cross-platform bootstrap, diagnostics, workstation profiles, CI, GPU smoke
  tests, an OpenUSD baseline, data/IP policies, and operator documentation.
- Validate the portable Python/C++/vision baseline on Windows and WSL2.

## Acceptance criteria

- Preserve `origin/main` and integrate all Ubuntu work that advanced during the
  task.
- Keep host data, models, recordings, generated USD, benchmarks, vendor SDKs,
  credentials, and company IP outside Git.
- Demonstrate bounded CUDA execution on the RTX 4070 Ti in Windows and WSL2.
- Produce a vendor-neutral OpenUSD artifact outside Git.
- Run relevant local quality gates, commit the work, push only the task branch,
  and leave an evidence-backed continuation point.

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

## Current checkpoint

- Branch: `win/bootstrap-desktop`
- Base: `origin/main` at `c01e9a1`
- Validated implementation baseline: `e387074`
- The working checkpoint includes documentation and executable-mode corrections
  for WSL-facing scripts.

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

## Verification evidence

- Windows Python: 49 passed; Ruff, formatting, Mypy (69 source files), and all
  pre-commit hooks passed.
- Windows C++: MSVC build passed; CTest 1/1 passed.
- Windows vision research: five acceptance groups passed.
- Windows GPU smoke: PyTorch 2.12.1+cu130, CUDA runtime 13.0, RTX 4070 Ti,
  compute capability 8.9, checksum 7.302420616149902, status PASS.
- WSL2 Python: 49 passed; Ruff, formatting, Mypy (69 source files), and all
  pre-commit hooks passed.
- WSL2 C++: GNU/Ninja build passed; CTest 1/1 passed.
- WSL2 vision research: five acceptance groups passed.
- WSL2 GPU smoke: PyTorch 2.12.1+cu130, CUDA runtime 13.0, RTX 4070 Ti,
  compute capability 8.9, checksum 7.302420616149902, status PASS.
- OpenUSD 26.8 created stages with `defaultPrim = World`, `metersPerUnit = 1`,
  and `upAxis = Z` on both Windows and WSL2.
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

## Blockers

- Isaac Sim scene validation requires a deliberately bounded workload and may
  still be constrained by VRAM below the official minimum.
- Ubuntu laptop GPU operability still requires its documented native-host test.
- Hardware and vendor integration require authorized devices, SDKs, safety
  review, and appropriately separated data.

## Modified files

- Workstation/CI/config: `.github/workflows/ci.yml`, `.gitattributes`,
  `.gitignore`, `.editorconfig`, `pyproject.toml`, `config/workstations/`.
- Runtime tools: `scripts/common/`, `scripts/windows/`, `scripts/wsl/`,
  `experiments/gpu/`, `experiments/openusd/`.
- Policy/docs: `docs/data/`, `docs/workstations/`, `docs/digital_twin/`,
  `docs/learning/openusd/`, `resources/openusd/`, `resources/rtx4070ti/`, plus
  updates to root architecture, roadmap, resource, and project documents.
- Tests: cross-platform workstation configuration and architecture/diagnostic
  boundary updates.

## Next concrete action

After review, merge `win/bootstrap-desktop` through the normal GitHub workflow.
Then check out that exact merge commit on Ubuntu, Windows, and WSL2 and run the
same core/vision replay benchmark suite to establish a three-environment parity
record before adding vendor or physical-hardware integration.
