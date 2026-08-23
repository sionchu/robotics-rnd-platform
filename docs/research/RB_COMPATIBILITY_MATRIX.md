# RB Compatibility Matrix

Verified 2026-08-23. Blank controller fields are deliberate; no controller was
available.

| Platform | rbpodo | Python | C++ | Ubuntu | ROS | Controller/model/firmware | Validation | Status |
|---|---|---|---|---|---|---|---|---|
| v0.3.0 | 0.16.14 source/API reviewed; optional and not installed in CI | 3.12 | C++17 source requirement reviewed | 24.04 | Jazzy optional; direct adapter is ROS-free | unknown / unknown / unknown | SOURCE_INSPECTION + MOCK_TEST + REPLAY_TEST | SOFTWARE_VALIDATED / HARDWARE_NOT_VALIDATED |
| v0.3.0 | absent | 3.12 | C++17 platform smoke | 24.04 | absent or present | none | generic/mock/replay CI | SUPPORTED |
| future LEVEL 1 | to record | to record | to record | to record | optional | to record | LIVE_READ_ONLY | NOT_RUN |

## Version policy

- Reviewed baseline is exactly rbpodo 0.16.14.
- The package is not a core dependency and is not blindly pinned into normal CI.
- The adapter checks distribution version and required attributes at runtime.
- Missing optional capabilities reduce the reported capability set rather than
  crashing unrelated state operations.
- A new minor/patch version triggers source/changelog/contract review before it
  enters this matrix.
- Controller firmware compatibility is never inferred from the Python package
  version; LEVEL 1 must record both.
