# Experiment 018 — UR10e Peg-in-Hole Learning Lab

## Question

Can a state-based UR10e peg-in-hole environment with a per-environment
randomized target expose a clear observation/action/reward contract and pass a
reproducible PPO pipeline smoke test without changing the reusable robotics
platform or Isaac Lab?

## Hypothesis

A fixed-orientation UR10e with a 3-D relative position command, a primitive
four-wall socket on a wide assembly plate, and ten target-relative state values
should be sufficient for the first randomized learning pipeline.  Contact force
is retained as a diagnostic rather than a policy input or reward term.

## Scope and status

This is an external Isaac Lab task.  It is registered by
`registration.register_tasks` and uses the pinned upstream UR10e asset,
manager-based environment, PhysX backend, differential IK action term, and
RSL-RL trainer.  No Isaac Lab source, root dependency, reusable platform
module, gripper, camera, ROS bridge, or generic RL wrapper is added.

Current classification:

- `TASK_UI_VERIFIED`
- `RANDOMIZED_TASK_VERIFIED`
- `PIPELINE_VERIFIED`
- `LEARNING_NOT_ESTABLISHED`

The 1,000-iteration baseline remains intentionally unrun.  The fixed-hole v0
pipeline evidence is retained below as historical evidence.

## External baseline

- Isaac Lab checkout: `C:\dev\IsaacLab`
- Exact commit: `418ca31b47a8eb27db8aefcfc134e4c4f1d2b6f3`
- Isaac Sim: `C:\isaacsim` pre-built binary, version `6.0.1`
- Bundled Python: `C:\dev\IsaacLab\_isaac_sim\kit\python\python.exe`
- Robot source: upstream `isaaclab_assets.robots.universal_robots.UR10e_CFG`
- Active task IDs: `Isaac-UR10e-PegInsert-Learning-v1` and
  `Isaac-UR10e-PegInsert-Learning-Play-v1`
- Historical v0 IDs: `Isaac-UR10e-PegInsert-Learning-v0` and
  `Isaac-UR10e-PegInsert-Learning-Play-v0`

The external task is imported with
`PYTHONPATH=C:\dev\robotics-rnd-platform`.  Generated logs, checkpoints,
TensorBoard files, videos, caches, and other large outputs remain outside the
tracked repository files.

## v1 Randomized Plate Task

The v1 scene makes the assembly relationship explicit: upstream UR10e → rigid
peg → wide plate/jig → one square socket.  The plate is a primitive
`0.44 × 0.34 × 0.04 m` body centered at
`(-0.6433276, -0.1740356, 0.0) m`.  The socket opening is a `50 mm` square
formed by four `20 mm`-thick primitive walls, giving the unchanged `10 mm`
nominal peg clearance.  No boolean CSG or concave collision mesh is used.

The plate is a simple collidable base whose top is the socket bottom at
`z = 0.020 m`.  The four walls are the authoritative side-contact geometry and
the success threshold stops `60 mm` below the hole top, well above that base.
This keeps the insertion region open for the measured task while making the
limitation explicit: this is not a CAD aperture or a deeper-than-bottom
insertion study.

The target marker and insertion-axis marker are primitive kinematic objects.
They are moved with the four walls at every reset, so the visual target and the
physical socket share one runtime hole frame.

## Hole randomization

At every reset, one XY offset is sampled independently for each environment
and applied to the hole center:

- X range: `[-0.040, +0.040] m` (`[-40, +40] mm`)
- Y range: `[-0.030, +0.030] m` (`[-30, +30] mm`)
- Z and orientation: fixed

The range was narrowed through deterministic multi-environment IK probes from
the initial wider candidates.  The final nine-environment probe sampled nine
distinct initial offsets and completed `18` deterministic episodes with
`18` successes and `0` timeouts/failures.  The range remains inside the plate
with primitive wall margins and avoids the singular/extreme poses seen outside
the tested region.

Hole workspace randomization is separate from the peg's initial alignment
error.  The latter remains a uniform `±15 mm` XY offset after the nominal
approach pose is solved.

## Runtime hole state

`learning_lab.py` stores `_hole_offset_xy` and `_hole_center_w` per
environment.  `reset_peg_insert` performs this sequence:

1. reset the upstream scene to defaults;
2. sample one hole XY offset per selected environment;
3. write the new world-space root pose and zero velocity to the four kinematic
   wall `RigidObject`s, the target marker, and the insertion-axis marker;
4. refresh the simulation tensors;
5. solve the nominal UR10e approach above the sampled hole with the existing
   damped-least-squares projection; and
6. add the unchanged `±15 mm` peg-relative initial XY error.

The indexed `RigidObject.write_root_pose_to_sim_index` and
`write_root_velocity_to_sim_index` calls update PhysX runtime state directly.
Task observations, rewards, success, and UI diagnostics read the live
articulation/contact tensors and `_hole_center_w`; no USD/Fabric transform
cache is used for task calculations.

## Observation equivalence

The v1 policy abstraction is unchanged from v0 and remains exactly ten values:

| Term | Shape | Units | Meaning |
| --- | ---: | --- | --- |
| `peg_pos_rel_hole` | 3 | m | Peg-tip position minus the current per-environment hole center |
| `peg_linear_velocity` | 3 | m/s | Peg-tip linear velocity in the world-aligned hole frame |
| `previous_action` | 3 | normalized | Previous environment action |
| `insertion_depth` | 1 | m | Clamped distance below the current hole top, `[0, HOLE_DEPTH]` |

No absolute hole world position, force input, observation noise, or corruption
was added.  Runtime inspection reported `Dict('policy': Box(..., (1, 10)))`,
policy shape `(1, 10)`, finite values, and action shape `(1, 3)`.  The earlier
32-observation/7-action expectation belonged to the separate Franka research
reconstruction, not this UR10e v0 contract.

## Action and reward contracts

The action remains `[Δx, Δy, Δz]` with three dimensions, relative Cartesian
position semantics, fixed orientation, differential IK, DLS `lambda = 0.02`,
and scale `0.005 m` per policy step.  The six upstream UR10e arm joints and
`wrist_3_link` body offset at the `120 mm` peg tip remain unchanged.

The reward manager still has exactly three conceptual terms:

1. `alignment_progress`, weight `2.0`;
2. `insertion_progress`, weight `3.0`, gated at `10 mm` lateral error; and
3. `success_bonus`, weight `10.0`.

Success remains `xy_error ≤ 5 mm` and `insertion_depth ≥ 60 mm`.  Timeout is
the fixed eight-second episode limit (`dt = 1/60 s`, decimation `2`, policy
step `1/30 s`).

## Reset and Learning UI

The native `LearningLabWindow` still delegates to Isaac Lab's
`ManagerBasedRLEnvWindow`.  Its panel preserves the pipeline

`Goal → Observation (10) → PPO Policy → ΔXYZ → Differential IK → UR10e / PhysX → Reward → Success`

and now adds live `Environment`, `Hole X/Y`, `Offset`, and
`Randomized each episode: YES` fields alongside XY error, Z error, insertion,
contact, episode step, success, actions, and reward terms.  The panel is kept
visible in the compact Kit window while the upstream control/debug frames stay
available as collapsible frames.

## PPO configuration

`UR10ePegInsertPPORunnerCfg` keeps the v0/Experiment 017 starting values:
actor/critic MLP hidden dimensions `[64, 64]`, ELU actor and critic, Gaussian
initial standard deviation `1.0`, `24` steps per environment, `8` learning
epochs, `4` mini-batches, adaptive learning rate `1e-3`, `γ=0.99`, `λ=0.95`,
desired KL `0.01`, clip `0.2`, and entropy coefficient `0.001`.  The registered
configuration still has `max_iterations=1000`; only the five-iteration smoke
was rerun for v1.

## v0 Historical Evidence

The fixed-hole v0 milestone is preserved here rather than treated as the v1
measurement:

- `TASK_UI_VERIFIED`: finite Kit GUI probe, deterministic axis/insertion probe,
  random probe, and timeout/reset checks completed.
- `RANDOM_BASELINE`: `128` episodes, `0` successes.
- `PIPELINE_VERIFIED`: pre-Kit import gate and exact five-iteration PPO smoke
  completed.
- `LEARNING_NOT_ESTABLISHED`: the five-iteration run was pipeline evidence
  only.
- `TRAINING_NOT_STARTED`: the 1,000-iteration baseline was not run.

The v0 random baseline used 64 environments, seed `42`, and normalized
`uniform[-0.3, 0.3]` actions for `128` complete episodes and `478` vectorized
policy steps:

| Metric | Result |
| --- | ---: |
| Completed episodes | 128 |
| Successes / success rate | 0 / 0.0% |
| Mean final XY error | 0.0141744 m (14.1744 mm) |
| Mean maximum insertion depth | 0.0000000 m |
| Mean episode length | 239 policy steps |
| Mean episodic reward | -0.000177807 |

The v0 log remains outside Git at
`C:\Users\getch\AppData\Local\Temp\exp018-random-baseline-20260828.log`.

The first v0 PPO callback attempt failed before rollout because it imported
Kit/PhysX-backed runtime classes while the official trainer was parsing
arguments.  `registration.py` was then introduced as a pre-Kit-safe callback
boundary with lazy runtime-term forwarders.  The captured failure remains at
`C:\Users\getch\AppData\Local\Temp\exp018-ppo-smoke-20260828.log`.

The exact v0 five-iteration command was:

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

It produced `64 × 24 × 5 = 7,680` transitions, TensorBoard events, and
checkpoints `model_0.pt` and `model_4.pt` under
`C:\dev\IsaacLab\logs\rsl_rl\ur10e_peg_insert_learning\2026-08-28_00-46-42_exp018_smoke_seed42`.
The event tags were:

`Episode_Reward/alignment_progress`,
`Episode_Reward/insertion_progress`, `Episode_Reward/success_bonus`,
`Episode_Termination/success`, `Episode_Termination/time_out`, `Loss/value`,
`Loss/surrogate`, `Loss/entropy`, `Loss/learning_rate`, `Policy/mean_std`,
`Perf/total_fps`, `Perf/collection_time`, `Perf/learning_time`,
`Train/mean_reward`, `Train/mean_episode_length`,
`Train/mean_reward/time`, and `Train/mean_episode_length/time`.

`Train/mean_reward` progressed from `-0.000191886` at iteration 0 to
`-0.00120919` at iteration 4; success remained `0.0` and mean episode length
progressed from `10.25` to `64.9143` steps.  The final reported
`Loss/value`, `Loss/surrogate`, `Loss/entropy`, `Loss/learning_rate`, and
`Policy/mean_std` values were `3.989e-05`, `-0.00617167`, `4.20812`,
`0.000666667`, and `0.981532`.

The v0 checkpoint hashes were:

- `model_0.pt`: `89B43394F8B100E9D3D19DD1A4C663920480F34D3CC0BC4B02F2362C6F957F2F`
- `model_4.pt`: `3E83D0DC8DF00AD06BD9AA0A22E0A425E8E3382EE1576DD75661028AE53CED1A`

The original wrapper warning about a missing
`_isaac_sim\setup_conda_env.bat` was preserved; the run still used Isaac Sim's
bundled Python.  PhysX reported the existing disjointed `ee_joint` transform
warning and RSL-RL reported that `obs_groups` omitted explicit `actor`/`critic`
keys.  The early v0 playback used `model_4.pt` and wrote a finite video to
`C:\dev\IsaacLab\logs\rsl_rl\ur10e_peg_insert_learning\2026-08-28_00-46-42_exp018_smoke_seed42\videos\play\rl-video-step-0.mp4`;
that visual check was not evidence of learning.  No generated v0 artifacts
were copied into this repository.

## v1 Verification Evidence

### Single-environment GUI and reset capture

The native Kit GUI run rendered the UR10e, orange peg, wide plate/socket,
markers, and Learning Lab panel.  The inspected desktop capture is external:

`C:\Users\getch\AppData\Local\Temp\exp018-v1-visual-single\desktop-ui-v1.png`

The panel showed `Observation (10)`, `dX dY dZ`, the v1 task mode, live hole
coordinates, hole offset, and `Randomized each episode: YES`.

Three consecutive seeded resets used the same renderer camera and were saved
outside Git:

| Reset | Seed | Hole offset (mm) | Capture |
| --- | ---: | ---: | --- |
| 1 | 42 | `[+9.037, +29.263]` | `C:\Users\getch\AppData\Local\Temp\exp018-v1-visual-single\randomization-plate-1.png` |
| 2 | 43 | `[-30.162, -20.237]` | `C:\Users\getch\AppData\Local\Temp\exp018-v1-visual-single\randomization-plate-2.png` |
| 3 | 44 | `[+11.649, -25.862]` | `C:\Users\getch\AppData\Local\Temp\exp018-v1-visual-single\randomization-plate-3.png` |

The runtime inspection log also recorded the corresponding wall, target-marker,
and insertion-axis-marker positions before and after reset, plus
`HOLE_CHANGED True`:

`C:\Users\getch\AppData\Local\Temp\exp018-v1-space-inspection.log`

### Deterministic multi-position probe

The final conservative range was tested with nine vectorized environments and
the transparent signed-axis/alignment/insertion controller.  Result:

| Sampled positions | Successful deterministic insertions | Failed/timeouts |
| ---: | ---: | ---: |
| 9 | 18 completed episodes | 0 |

The external log is
`C:\Users\getch\AppData\Local\Temp\exp018-v1-deterministic-9env-narrow.log`.
This is a task-validity oracle, not learned behavior.

### Parallel environment preview

The nine-environment Kit preview used the normal Isaac Lab vectorized scene.
The inspected frame shows nine UR10e/plate/socket copies with the parallel
layout; each copy owns one sampled hole state.  It is external at
`C:\Users\getch\AppData\Local\Temp\exp018-v1-visual-parallel\frame-015.png`.
The corresponding video is at
`C:\Users\getch\AppData\Local\Temp\exp018-v1-visual-parallel\rl-video-step-0.mp4`.

### 64-environment runtime gate

The finite headless PhysX gate ran `64` environments for `30` policy steps
with random actions.  It reported:

```text
envs=64, steps=30, obs_shape=(64, 10), action_shape=(64, 3), action_dim=3,
finite=True, max_abs_obs=0.3362036, terminated=0, truncated=0
```

The external log is
`C:\Users\getch\AppData\Local\Temp\exp018-v1-64env-runtime-gate.log`.

### Random Baseline v1

Classification: `RANDOM_BASELINE_V1`.

The changed task was remeasured with `64` environments, seed `42`, and
normalized `uniform[-0.3, 0.3]` actions.  It completed `128` episodes in
`478` vectorized policy steps:

| Metric | Result |
| --- | ---: |
| Completed episodes | 128 |
| Successes / success rate | 0 / 0.0% |
| Mean final XY error | 0.0136548132 m (13.6548 mm) |
| Mean maximum insertion depth | 0.0000000 m |
| Mean episode length | 239 policy steps |
| Mean episodic reward | -0.0001485529 |
| Sampled peak VRAM | 4,328 MB |
| Measurement wall time | 26.481 s (12.726 s rollout) |

The deterministic insertion controller was not used.  The full generated log
remains at
`C:\Users\getch\AppData\Local\Temp\exp018-v1-random-baseline-20260828.log`.

### PPO Smoke v1

The exact five-iteration v1 command was:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat train `
  --rl_library rsl_rl `
  --task Isaac-UR10e-PegInsert-Learning-v1 `
  --num_envs 64 `
  --max_iterations 5 `
  --seed 42 `
  --deterministic `
  --headless `
  --logger tensorboard `
  --run_name exp018_v1_smoke_seed42 `
  --device cuda:0 `
  --external_callback experiments.robot.018_ur10e_peg_in_hole.registration.register_tasks
```

The command exited `0`.  It produced five iterations and
`64 × 24 × 5 = 7,680` transitions.  Trainer time was `7.22 s`; wall time
including Kit startup/shutdown was `22.419 s`.  The external run directory is

`C:\dev\IsaacLab\logs\rsl_rl\ur10e_peg_insert_learning\2026-08-28_01-29-47_exp018_v1_smoke_seed42`

and contains `model_0.pt`, `model_4.pt`, and a TensorBoard event file.  The
checkpoint SHA-256 values are:

- `model_0.pt`: `12E92FF07BDDAC032406305B0A61BFA5E7958147B02D71654C64070C463A4B78`
- `model_4.pt`: `694B437BD38B0ADA0C2D358DD0ED60A8416A4A695C5445AFED4C32526E44E95B`

The emitted TensorBoard tags were:

`Episode_Reward/alignment_progress`,
`Episode_Reward/insertion_progress`, `Episode_Reward/success_bonus`,
`Episode_Termination/success`, `Episode_Termination/time_out`, `Loss/value`,
`Loss/surrogate`, `Loss/entropy`, `Loss/learning_rate`, `Policy/mean_std`,
`Perf/total_fps`, `Perf/collection_time`, `Perf/learning_time`,
`Train/mean_reward`, `Train/mean_episode_length`,
`Train/mean_reward/time`, and `Train/mean_episode_length/time`.

The reported `Train/mean_reward` values were
`-0.0002275561`, `-0.0005394704`, `-0.0006139899`, `-0.0007495283`, and
`-0.0011738124` across iterations 0–4.  Success remained `0.0`; mean episode
length progressed `14.7692`, `22.6190`, `29.5`, `34.9310`, and `47.0` steps.
These five iterations establish the revised pipeline path only; they do not
establish learning.

Warnings preserved in the external log include the pre-built-binary wrapper
notice for missing `_isaac_sim\setup_conda_env.bat`, the expected Windows
`libcarb.so` Fabric notice, noisy-velocity/TGS and disjointed `ee_joint` PhysX
warnings, RSL-RL `obs_groups` fallback warnings, and the optional
`isaaclab_visualizers` extension configuration warning.

## Files changed

The v1 change is intentionally limited to the existing canonical Experiment
018 files:

- `README.md` — active v1 contract, v0 historical evidence, and measured v1 evidence;
- `registration.py` — v1 IDs, primitive plate/socket scene, and unchanged manager/PPO configuration;
- `learning_lab.py` — per-environment runtime hole state, socket pose writes, reset sampling, UI fields, and probe reporting.

No generated logs, checkpoints, TensorBoard events, videos, caches, root
dependencies, reusable-platform modules, Isaac Lab files, or helper scripts are
tracked.
