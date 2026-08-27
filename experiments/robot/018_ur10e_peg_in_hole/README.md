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
`registration.register_tasks` and uses the pinned upstream UR10e asset,
manager-based environment, PhysX backend, differential IK action term, and
RSL-RL trainer.  No Isaac Lab source, root dependency, reusable platform
module, gripper, camera, ROS bridge, or generic RL wrapper is added.

`TASK_UI_VERIFIED`: `true` after the finite Kit GUI probe, deterministic
axis/insertion probe, random probe, and timeout/reset checks completed.
`PIPELINE_VERIFIED`: `true` after the pre-Kit import gate and the exact
five-iteration PPO pipeline smoke completed.
`LEARNING_NOT_ESTABLISHED`: `true`; five iterations are pipeline evidence only.
`TRAINING_NOT_STARTED`: true for the 1,000-iteration baseline, which remains
out of scope for this smoke.

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

## PPO configuration and pipeline smoke

`UR10ePegInsertPPORunnerCfg` follows the official Experiment 017 RSL-RL
starting values: actor/critic MLP hidden dimensions `[64, 64]`, ELU actor and
critic, Gaussian initial standard deviation `1.0`, 24 steps per environment,
8 learning epochs, 4 mini-batches, adaptive learning rate `1e-3`, `γ=0.99`,
`λ=0.95`, desired KL `0.01`, clip `0.2`, and entropy coefficient `0.001`.
The registered configuration has `max_iterations=1000`; the first official CLI
smoke is intentionally capped at five iterations and is recorded below.  The
1,000-iteration baseline was not run.

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

## Registration boundary and PPO pipeline smoke

The first PPO CLI attempt failed before rollout because the callback imported
`learning_lab.py` while the official trainer was still parsing arguments.  That
module imported Kit/PhysX-backed runtime classes at module scope, so the later
SimulationApp saw preloaded `pxr`, `omni.usd`, and `omni.physx` modules.  The
captured failure remains outside Git at
`C:\Users\getch\AppData\Local\Temp\exp018-ppo-smoke-20260828.log`.

The fix adds `registration.py`.  It owns the constants, Gym registration,
environment/PPO config classes, and only explicit lazy manager-term forwarders;
it never imports `learning_lab` at module import.  The registry now points to
`registration.register_tasks`, runtime entry point
`learning_lab:UR10ePegInsertEnv`, and config entry points in
`registration.py`.

A fresh bundled-Python pre-Kit test imported the registration callback, loaded
both config types, and confirmed that `learning_lab`, `pxr`, `omni.usd`, and
`omni.physx` were absent from `sys.modules` before SimulationApp.  The finite
deterministic probe then instantiated the task with `obs_dim=(10,)` and
`action_dim=3`, produced finite tensors, reset successfully, and reached the
task's success termination at steps 140 and 233.

The exact five-iteration retry command was run once:

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
  --external_callback experiments.robot.018_ur10e_peg_in_hole.registration.register_tasks
```

The run completed with batch exit code `0`, five iterations, and 7,680
transitions (`64 × 24 × 5`).  It emitted a TensorBoard event file and saved
`model_0.pt` and `model_4.pt` under:

`C:\dev\IsaacLab\logs\rsl_rl\ur10e_peg_insert_learning\2026-08-28_00-46-42_exp018_smoke_seed42`

The run used seed `42`, `cuda:0`, PhysX, and the configured 24 steps per
environment.  The event tags were:

`Episode_Reward/alignment_progress`,
`Episode_Reward/insertion_progress`, `Episode_Reward/success_bonus`,
`Episode_Termination/success`, `Episode_Termination/time_out`, `Loss/value`,
`Loss/surrogate`, `Loss/entropy`, `Loss/learning_rate`, `Policy/mean_std`,
`Perf/total_fps`, `Perf/collection_time`, `Perf/learning_time`,
`Train/mean_reward`, `Train/mean_episode_length`,
`Train/mean_reward/time`, and `Train/mean_episode_length/time`.

`Train/mean_reward` progressed from `-0.000191886` at iteration 0 to
`-0.00120919` at iteration 4; success remained `0.0` in all five iterations.
`Train/mean_episode_length` progressed from `10.25` to `64.9143` steps.  The
final `Loss/value`, `Loss/surrogate`, `Loss/entropy`, `Loss/learning_rate`, and
`Policy/mean_std` values were `3.989e-05`, `-0.00617167`, `4.20812`,
`0.000666667`, and `0.981532` respectively.

Checkpoint hashes (SHA-256) are recorded here for reproducibility:

- `model_0.pt`: `89B43394F8B100E9D3D19DD1A4C663920480F34D3CC0BC4B02F2362C6F957F2F`
- `model_4.pt`: `3E83D0DC8DF00AD06BD9AA0A22E0A425E8E3382EE1576DD75661028AE53CED1A`

The original wrapper warning about a missing `_isaac_sim\setup_conda_env.bat`
was preserved; the run nevertheless used Isaac Sim's bundled Python.  PhysX
also reported the existing disjointed `ee_joint` transform warning and RSL-RL
reported that `obs_groups` omitted explicit `actor`/`critic` keys.

## Early PPO Visual Check

The official `play` command loaded `model_4.pt` with the same registration
callback, `--num_envs 1`, seed `42`, PhysX, and the Kit visualizer.  A finite
120-step video completed and was written to:

`C:\dev\IsaacLab\logs\rsl_rl\ur10e_peg_insert_learning\2026-08-28_00-46-42_exp018_smoke_seed42\videos\play\rl-video-step-0.mp4`

The MP4 is 4.0 s (373,536 bytes); a rendered mid-run frame showed the UR10e
and attached peg in the Isaac Sim viewport.  This is an early pipeline visual
check only, not evidence that PPO learned the task.

## Current Classification

- `TASK_UI_VERIFIED`
- `PIPELINE_VERIFIED`
- `LEARNING_NOT_ESTABLISHED`
