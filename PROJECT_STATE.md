# Project State

Updated: 2026-08-24
Machine role: Windows RTX desktop with a WSL2 companion environment

## Current stable capabilities

- Generic Python robotics contracts, deterministic mock robot/camera providers,
  frame transforms, diagnostics, structured configuration, and a mock guidance
  application.
- Synthetic vision foundation for camera calibration, AprilTag detection, PnP,
  transform chains, sensitivity studies, and reproducible benchmark records.
- Cross-platform Python and C++ build/test gates for Ubuntu, Windows, and WSL2.
- Conservative Windows and WSL bootstrap/doctor scripts that do not install
  drivers, vendor SDKs, ROS, Docker, or Isaac Sim.
- PyTorch CUDA smoke benchmarking on the Windows RTX desktop and its WSL2
  environment.
- Vendor-neutral OpenUSD stage generation with explicit metric and axis metadata.
- Workcell Exchange Schema 1.0 with equivalent JSON/YAML manifests, required
  frame roles, normalized XYZW transforms, core-backed graph validation, and a
  manifest-driven OpenUSD workcell.
- Raspberry Pi camera edge capture/replay contracts, physical-measurement
  preparation, and hardware-independent CLI/tests from the Ubuntu v0.2.1
  milestone. Physical Pi execution remains pending.
- Data, model, asset, recording, and company-IP separation rules that keep large
  or restricted material outside Git.

## Current branch/version

- Integration branch: `win/bootstrap-desktop`
- Base: `origin/main` at `a545a2b`
- Package version: `0.2.1`

## Latest validated commit

- `1807ef9` — merged Ubuntu's Raspberry Pi edge milestone into the Workcell
  Exchange/Windows branch and hardened POSIX peak-memory telemetry for Windows.
- The final documentation/executable-mode checkpoint is the current `HEAD` on
  `win/bootstrap-desktop`.

## Ubuntu validation status

- The Ubuntu v0.2 foundation on `origin/main` records 48 passing Python tests,
  all five synthetic vision acceptance groups passing, strict Ruff and Mypy
  gates, and CTest 1/1 passing.
- The Ubuntu laptop's RTX 5060 is kernel-visible, but its native GPU execution
  remains outside the current desktop task. No Ubuntu driver or repository state
  was changed from Windows.

## Windows validation status

- Windows 11, Python 3.12.10 repository environment, MSVC 19.44, CMake 4.1.1,
  Ninja 1.13.2, and Git 2.48.1.
- Python: 69 tests passed with 1 hardware test deselected; Ruff, Ruff formatting,
  Mypy, and pre-commit passed.
- Native C++: Visual Studio generator build passed; CTest 1/1 passed.
- Vision research: all five synthetic acceptance groups passed.
- PyTorch 2.12.1 with CUDA 13.0 successfully executed the RTX 4070 Ti smoke
  workload at compute capability 8.9.
- OpenUSD 26.8 generated and reopened the manifest-driven metric Z-up workcell
  from both JSON and YAML.

## WSL validation status

- Ubuntu 24.04.3 under WSL2 with Python 3.12.3, GCC/G++ 13.3, CMake 3.28.3,
  Ninja 1.13.0, and Git 2.43.0.
- Python: 69 tests passed with 1 hardware test deselected; Ruff, Ruff formatting,
  Mypy, and pre-commit passed.
- Native C++: Ninja/GNU build passed; CTest 1/1 passed.
- Vision research: all five synthetic acceptance groups passed.
- PyTorch 2.12.1 with CUDA 13.0 successfully executed the RTX 4070 Ti smoke
  workload at compute capability 8.9.
- OpenUSD 26.8 generated and reopened the manifest-driven workcell in the
  external WSL data root.

## Known hardware-only tests

- Live camera calibration and physical AprilTag measurements.
- Authorized Rainbow robot connection, state, I/O, and motion behavior.
- Mech-Eye/Mech-Vision acquisition through an official SDK environment.
- Ubuntu laptop host GPU test outside the prior isolated execution environment.
- Physical Raspberry Pi camera bring-up and experiments 006–012.

## Known simulation-only tests

- Isaac Sim scene launch, RTX rendering, sensor simulation, and sustained VRAM
  behavior.
- Workcell replay mapping and simulation-to-replay parity.

## Known blockers

- Isaac Sim 6.0.1 is present on Windows, but the RTX 4070 Ti has 12,282 MiB and
  is below NVIDIA's published 16 GB minimum VRAM. Only the packaged compatibility
  checker has been run; no scene workload has been accepted as stable.
- Docker is not installed on Windows or WSL2.
- The CUDA Toolkit compiler (`nvcc`) is not installed; current GPU work uses the
  CUDA runtime packaged with PyTorch.
- WSL2 does not have GitHub CLI; Git fetch works through command-scoped Windows
  Git Credential Manager integration.
- Raspberry Pi physical evidence is pending the repository's documented hardware
  handoff and does not block hardware-independent PR review.

## Next recommended task

Review and merge `win/bootstrap-desktop`. Then pin the merge commit in the future
`manufacturing-digital-twin-rnd` repository and implement its first schema
consumer contract test before adding manufacturing or simulation concepts.
