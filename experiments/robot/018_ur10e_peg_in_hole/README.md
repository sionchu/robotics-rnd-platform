# Experiment 018 — UR10e Peg-in-Hole Learning Lab v0

## Question

Can a small, state-based UR10e peg-in-hole environment expose a clear
observation/action/reward contract that is ready for a reproducible PPO
experiment without changing the reusable robotics platform or Isaac Lab?

## Hypothesis

A fixed-orientation UR10e with a 3-D relative position command, four primitive
hole walls, and ten state values should be sufficient for a first learning
pipeline smoke test.  Contact force is retained as a diagnostic rather than a
policy input or reward term.

## Scope and status

This is an external Isaac Lab task.  It is registered by
`learning_lab.register_tasks` and uses the pinned upstream UR10e asset,
manager-based environment, PhysX backend, differential IK action term, and
RSL-RL trainer.  No Isaac Lab source, root dependency, reusable platform
module, gripper, camera, ROS bridge, or generic RL wrapper is added.

`TASK_UI_VERIFIED`: `true` after the finite Kit GUI probe, deterministic
axis/insertion probe, random probe, and timeout/reset checks completed.
`TRAINING_NOT_STARTED`: true.  A 1,000-iteration PPO run is intentionally not
part of v0 implementation.

## External baseline

- Isaac Lab checkout: `C:\dev\IsaacLab`
- Exact commit: `418ca31b47a8eb27db8aefcfc134e4c4f1d2b6f3`
- Isaac Sim: `C:\isaacsim` pre-built binary, version `6.0.1`
- Robot source: upstream `isaaclab_assets.robots.universal_robots.UR10e_CFG`
- Task IDs: `Isaac-UR10e-PegInsert-Learning-v0` and
  `Isaac-UR10e-PegInsert-Learning-Play-v0`

The external task is imported with `PYTHONPATH=C:\dev\robotics-rnd-platform`.
Generated logs, checkpoints, TensorBoard files, videos, caches, and other
large outputs must remain outside the tracked repository files.

## Scene

`SceneCfg` contains:

- the fixed-base upstream UR10e at `{ENV_REGEX_NS}/Robot`;
- a 40 mm × 40 mm × 120 mm orange peg attached to
  `wrist_3_link` at local `(0, 0, 60 mm)`;
- a magenta peg-tip marker attached to `wrist_3_link` at local `(0, 0, 120 mm)`;
- a collidable fixture base and four primitive box walls around a 50 mm
  square opening;
- a green hole-target marker and blue insertion-axis marker;
- a ground plane, dome light, and a PhysX contact sensor on `wrist_3_link`.

The opening is 10 mm wider than the peg, giving 5 mm nominal side clearance.
The fixture uses the validated reachable XY location
`(-0.6433276, -0.1740356) m`; the hole top and bottom are `0.3061152 m` and
`0.0200 m` in the environment frame.

## Coordinate frames and runtime state

The robot base/root is the fixed reference for IK.  `wrist_3_link` is the
upstream terminal body.  The peg reference is the wrist body plus the local
peg-tip offset `(0, 0, 120 mm)`.  The hole frame is aligned with the world and
environment axes.  All observations are computed from live articulation and
contact-sensor tensors; no USD transform cache is used.

## Observation (policy: 10 values)

The concatenated policy vector is ordered as follows:

| Term | Shape | Units | Meaning |
| --- | ---: | --- | --- |
| `peg_pos_rel_hole` | 3 | m | Peg tip position minus hole center in the hole frame |
| `peg_linear_velocity` | 3 | m/s | Peg-tip linear velocity in the hole/world-aligned frame |
| `previous_action` | 3 | normalized | Previous environment action |
| `insertion_depth` | 1 | m | Clamped distance below the hole top, `[0, HOLE_DEPTH]` |

There is no observation noise or corruption in v0.  Contact force, Z error,
and success state are UI/diagnostic values only.

## Action (3 values)

`ActionsCfg.arm_action` is the official
`DifferentialInverseKinematicsActionCfg` with:

- `command_type="position"` and `use_relative_mode=True`;
- `ik_method="dls"`, `lambda_val=0.02`;
- `body_name="wrist_3_link"` and a 120 mm peg-tip body offset;
- six upstream UR10e arm joints;
- raw action `[Δx, Δy, Δz]` in `[-1, 1]`, scaled by `0.005 m` per policy step.

No orientation or gripper action is exposed.  The reset pose keeps the
official orientation and the first probe only commands translation.

## Reward (exactly three conceptual terms)

The reward manager has only these terms; each is multiplied by its configured
weight and environment step time:

1. `alignment_progress` — reduction in lateral XY error, weight `2.0`.
2. `insertion_progress` — increase in insertion depth while XY error is at
   most `10 mm`, weight `3.0`.
3. `success_bonus` — terminal success indicator, weight `10.0`.

There are no force, orientation, velocity, or action-rate penalties in v0.

## Reset, success, and timeout

Every reset starts from a fixed nominal approach pose, 25 mm above the hole
top, solved from the upstream default pose with damped Jacobian IK, then applies
a small uniform XY offset in `[-15, 15] mm`.  Orientation, geometry, and
physics parameters are not randomized.  Success is `xy_error ≤ 5 mm` and
`insertion_depth ≥ 60 mm`, a reproducible partial insertion before side-wall
contact in this v0 fixture.  Timeout is the fixed 8 s episode limit
(`dt = 1/60 s`, decimation `2`, policy step `1/30 s`).

## Learning UI and finite probe

`LearningLabWindow` delegates to Isaac Lab's native
`ManagerBasedRLEnvWindow` and adds a native `omni.ui` panel.  It shows the
pipeline, mode, XY/Z error, insertion depth, contact force, episode step,
success, raw/scaled actions, reward term values, and frame/unit terminology.
It updates through Kit's post-update event stream and does not start a web
server or add a browser frontend.  With Isaac Lab 3.0's explicit Kit
visualizer, the task attaches this native window after manager setup because
the visualizer path does not set `sim.has_gui`.

The finite script supports `manual` (zero action), `deterministic` (signed axis
pulses followed by a transparent hand-coded alignment/insertion probe), and
`random` actions:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\018_ur10e_peg_in_hole\learning_lab.py --task Isaac-UR10e-PegInsert-Learning-v0 --num_envs 1 --steps 240 --mode deterministic --viz kit
```

This probe is for GUI/runtime verification only; it is not a learned policy
and must not be reported as PPO training.

## PPO configuration (created for the later gate, not run here)

`UR10ePegInsertPPORunnerCfg` follows the official Experiment 017 RSL-RL
starting values: actor/critic MLP hidden dimensions `[64, 64]`, ELU actor and
critic, Gaussian initial standard deviation `1.0`, 24 steps per environment,
8 learning epochs, 4 mini-batches, adaptive learning rate `1e-3`, `γ=0.99`,
`λ=0.95`, desired KL `0.01`, clip `0.2`, and entropy coefficient `0.001`.
The registered configuration has `max_iterations=1000`, but no trainer command
is part of the v0 task configuration; the first official CLI smoke result is
recorded below.

## Verification gate

The finite GUI/runtime gate is complete for the v0 task:

- Kit visualizer run (`--viz kit`) rendered the UR10e, attached orange peg,
  fixture, target marker, and live Learning Lab panel in an Isaac Lab window.
- Deterministic axis/alignment/insertion probe reached `terminated=True` at
  step 140 with the 60 mm insertion success threshold.
- Zero-action probe reached `truncated=True` at step 238 and reset to the
  nominal approach pose.
- Random-action probe ran 30 steps and exited with code 0.

The probe is not a learned policy.  PPO configuration is present for the later
experiment; no PPO iteration has completed, and the random baseline is
documented below.

## Random Policy Baseline

Classification: `RANDOM_BASELINE`.

The unchanged task was run with 64 vectorized environments, seed `42`, and the
same conservative random action source as the finite probe:
`uniform[-0.3, 0.3]` in normalized action units.  The one-off measurement
collected 128 complete episodes (478 vectorized policy steps):

| Metric | Result |
| --- | ---: |
| Completed episodes | 128 |
| Successes / success rate | 0 / 0.0% |
| Mean final XY error | 0.0141744 m (14.1744 mm) |
| Mean maximum insertion depth | 0.0000000 m |
| Mean episode length | 239 policy steps |
| Mean episodic reward | -0.000177807 |

The deterministic insertion controller was not used for this baseline.  The
full generated log remains outside Git at
`C:\Users\getch\AppData\Local\Temp\exp018-random-baseline-20260828.log`.

## PPO Pipeline Smoke

The pinned official command was used exactly once after registration and
baseline checks:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat train `
  --rl_library rsl_rl `
  --task Isaac-UR10e-PegInsert-Learning-v0 `
  --num_envs 64 `
  --max_iterations 5 `
  --seed 42 `
  --deterministic `
  --headless `
  --logger tensorboard `
  --run_name exp018_smoke_seed42 `
  --device cuda:0 `
  --external_callback experiments.robot.018_ur10e_peg_in_hole.learning_lab.register_tasks
```

The batch wrapper returned exit code `0`, but the trainer log contains a fatal
`RuntimeError: Caught an unknown exception!` during Isaac Sim extension startup
before environment rollout.  The callback imports pxr-backed modules while the
official trainer is still parsing arguments; the subsequent SimulationApp
startup reports preloaded USD modules and failed `omni.kit.usd.layers`,
`omni.physx`, and pxr converter initialization.  No PPO iteration completed.

The captured log is outside Git at
`C:\Users\getch\AppData\Local\Temp\exp018-ppo-smoke-20260828.log`.

## Early PPO Visual Check

`NOT_RUN`: the smoke did not produce a usable checkpoint, so the Learning UI
was not switched to an Early PPO policy.  The existing native UI remains task
UI evidence only; no learned-policy comparison is reported.

## Current Classification

- `TASK_UI_VERIFIED`
- `PIPELINE_VERIFIED`: not established; trainer startup stopped before rollout
- `LEARNING_NOT_ESTABLISHED`
