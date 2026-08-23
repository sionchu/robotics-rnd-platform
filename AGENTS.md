# Agent Instructions

## Scope and safety

This is a private generic robotics research platform. Keep KAI Robotics Vision,
company work, production assets, vendor SDKs, and this repository separate. Read
`SECURITY_AND_IP.md` before handling external code, hardware, captures, network
settings, or credentials. Never operate physical hardware unless the task
explicitly authorizes it and a reviewed safety procedure exists.

## Research principles

1. Learn before abstraction.
2. Experiment before integration.
3. Prefer reproducible experiments.
4. Keep hardware/vendor-specific logic isolated.
5. Keep core algorithms hardware agnostic where practical.
6. Tests should not require physical hardware when mock/replay can validate behavior.
7. Document significant engineering decisions.
8. Preserve useful failed experiments and their conclusions.
9. Do not add dependencies without written justification.
10. Prefer official technical documentation.
11. Do not silently expand scope.
12. Audit aggressively; modify conservatively.

## Architectural invariants

- Core uses meters, radians, UTC timestamps, normalized XYZW quaternions, and
  explicit frames. `T_target_source` maps source coordinates into target.
- Core must not import ROS 2, `rbpodo`, Mech-Eye modules, Raspberry Pi modules,
  CUDA/Isaac APIs, PyTorch, or camera-vendor SDKs.
- Applications and skills depend on interfaces; drivers implement interfaces.
- Vendor objects, enums, status codes, and units never cross driver boundaries.
- A mock proves contract behavior, not physics, latency, safety, or hardware compatibility.

## Development workflow

Before implementation:

1. Read relevant docs and decisions.
2. Inspect current code and tests.
3. State the local scope.
4. Make the smallest coherent change.
5. Test it in proportion to risk.
6. Update docs when architecture or behavior changes.

Before every commit, inspect status and staged files, scan for secrets/private
data, run relevant tests, and run `git diff --check`. Never use destructive Git
commands against existing work. Keep generated data, models, captures, build
outputs, and vendor files untracked.

## Workstation and Git policy

- `origin/main` is the integrated source of truth; use short-lived task branches.
- Ubuntu laptop, Windows native, and Windows WSL2 use separate clones, virtual
  environments, build directories, and caches.
- Start by fetching, fast-forwarding `main`, and creating one task branch. Never
  force-push or choose one side wholesale in source-of-truth document conflicts.
- Git carries code, small configuration, and manifests. Data/model/capture/large
  asset bytes follow `docs/data/DATA_POLICY.md` outside Git.
- Ubuntu remains the primary real-hardware lab. Windows/WSL GPU, simulation, or
  replay results do not authorize robot motion or vendor-hardware operation.
- Isaac, OpenUSD, CUDA, PyTorch, ROS, and vendor SDKs remain optional adapters or
  experiment dependencies and never enter `robotics_rnd.core`.

## Research promotion gate

Code moves from `experiments/` into `src/` only when the hypothesis, environment,
metrics, result, limitations, API, units/frames, tests, and decision are recorded.
A hardware-dependent result needs replay data or a simulator path where practical.

## Task naming

Use one clear goal per task and these prefixes in logs/handoffs:

```text
[PLAN] [FEAT] [BUG] [REFACTOR] [TEST] [DOC] [EXP] [RESEARCH]
```
