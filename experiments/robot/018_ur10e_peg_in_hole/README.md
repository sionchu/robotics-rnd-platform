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
- `LEARNING_ESTABLISHED`
- `IN_DISTRIBUTION_HOLDOUT_VERIFIED`

The unchanged v1 1,000-iteration PPO baseline and deterministic checkpoint
evaluation are recorded below.  The fixed-hole v0 pipeline evidence is
retained below as historical evidence.

## External baseline

- Isaac Lab checkout: `C:\dev\IsaacLab`
- Exact commit: `418ca31b47a8eb27db8aefcfc134e4c4f1d2b6f3`
- Isaac Sim: `C:\isaacsim` pre-built binary, version `6.0.1`
- Bundled Python: `C:\dev\IsaacLab\_isaac_sim\kit\python\python.exe`
- Bundled Python runtime: `3.12.13`
- PyTorch: `2.10.0+cu128` (torch CUDA `12.8`, `torch.cuda.is_available() = True`)
- RSL-RL: `rsl-rl-lib 5.0.1`
- GPU: `NVIDIA GeForce RTX 4070 Ti` (driver `591.86`, 12,282 MiB reported)
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
configuration still has `max_iterations=1000`; the five-iteration smoke and the
first unchanged 1,000-iteration baseline are recorded below.

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

## v1 Meaningful PPO Baseline

### Training Run

The first unchanged v1 baseline used the official Isaac Lab trainer, the
external task callback, RSL-RL `5.0.1`, seed `42`, `64` environments, `24`
steps per environment, PhysX, CUDA, headless Kit, and TensorBoard:

```powershell
$log = 'C:\Users\getch\AppData\Local\Temp\exp018-v1-baseline-seed42.log'
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat train `
  --rl_library rsl_rl `
  --task Isaac-UR10e-PegInsert-Learning-v1 `
  --num_envs 64 `
  --max_iterations 1000 `
  --seed 42 `
  --deterministic `
  --headless `
  --logger tensorboard `
  --run_name exp018_v1_baseline_seed42 `
  --device cuda:0 `
  --external_callback experiments.robot.018_ur10e_peg_in_hole.registration.register_tasks *> $log
```

The command exited `0`.  It ran from
`2026-08-27T17:40:21.4905920Z` through
`2026-08-27T18:10:21.5656829Z`: wrapper wall time `1,800.05 s`, with trainer
reported training time `1,780.84 s`.  The final trainer line was
`Learning iteration 999/1000`, with exactly
`64 × 24 × 1000 = 1,536,000` environment transitions.

The external run directory is

`C:\dev\IsaacLab\logs\rsl_rl\ur10e_peg_insert_learning\2026-08-28_02-40-31_exp018_v1_baseline_seed42`

and the complete redirected log remains at
`C:\Users\getch\AppData\Local\Temp\exp018-v1-baseline-seed42.log`.

### Learning Curves

The event file emitted these task and trainer tags:

`Episode_Reward/alignment_progress`,
`Episode_Reward/insertion_progress`, `Episode_Reward/success_bonus`,
`Episode_Termination/success`, `Episode_Termination/time_out`, `Loss/value`,
`Loss/surrogate`, `Loss/entropy`, `Loss/learning_rate`, `Policy/mean_std`,
`Perf/total_fps`, `Perf/collection_time`, `Perf/learning_time`,
`Train/mean_reward`, `Train/mean_episode_length`,
`Train/mean_reward/time`, and `Train/mean_episode_length/time`.

Task-facing progression sampled from TensorBoard (`999` is the final event
for the `1000`-iteration run):

| Iteration | Mean reward | Mean episode length | Alignment reward | Insertion reward | Success bonus | Success | Time-out |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | -0.0002275561 | 14.7692 | -0.0000519364 | 0.0000000000 | 0.0000000000 | 0.0000 | 0.0866 |
| 100 | 0.0875914916 | 208.4600 | 0.0000361454 | 0.0008128257 | 0.0034722225 | 0.3190 | 0.6810 |
| 250 | 0.3434434235 | 58.2500 | 0.0000497039 | 0.0013874609 | 0.0416666679 | 1.0000 | 0.0000 |
| 500 | 0.3389396667 | 28.8500 | 0.0000462484 | 0.0010688945 | 0.0413194448 | 0.9902 | 0.0098 |
| 750 | 0.3383373916 | 25.6700 | 0.0000475335 | 0.0010365272 | 0.0412326418 | 0.9863 | 0.0137 |
| 999 | 0.3414654136 | 21.5100 | 0.0000455818 | 0.0009533769 | 0.0416666679 | 1.0000 | 0.0000 |

Optimizer progression:

| Iteration | Value loss | Surrogate loss | Entropy | Learning rate | Policy mean std |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.0066048447 | -0.0138215972 | 4.2718801498 | 0.0015000000 | 1.0087829828 |
| 100 | 0.0007274114 | -0.0066382703 | 2.4583601952 | 0.0000759375 | 0.5713808537 |
| 250 | 0.0004787729 | -0.0079200417 | 1.4438188076 | 0.0003844336 | 0.4134729207 |
| 500 | 0.0003663404 | -0.0005662279 | -0.4856194556 | 0.0002562891 | 0.2411780357 |
| 750 | 0.0002415750 | -0.0027804510 | -1.3534421921 | 0.0000759375 | 0.1757015735 |
| 999 | 0.0005307611 | 0.0011868129 | -2.4227828979 | 0.0001139063 | 0.1333562881 |

The reward and success curves are reported separately: the observed reward
increase is accompanied by a high `Episode_Termination/success` value, while
the configured adaptive learning-rate tag is the value emitted by RSL-RL.

### Checkpoint Evidence

The trainer wrote these external checkpoints:

`model_0.pt`, `model_50.pt`, `model_100.pt`, `model_150.pt`,
`model_200.pt`, `model_250.pt`, `model_300.pt`, `model_350.pt`,
`model_400.pt`, `model_450.pt`, `model_500.pt`, `model_550.pt`,
`model_600.pt`, `model_650.pt`, `model_700.pt`, `model_750.pt`,
`model_800.pt`, `model_850.pt`, `model_900.pt`, `model_950.pt`, and
`model_999.pt`.

The selected evaluation checkpoint is `model_999.pt` (136,059 bytes),
SHA-256
`D5D9AED8CA05D6BF5A9E64357BE146DD8E10782646ADEDC3E255A962CCF7CFAF`.
The trainer did not emit a separate `best_model`; no best-checkpoint claim is
made.

### Resource Usage

The same workstation reported `NVIDIA GeForce RTX 4070 Ti`, driver `591.86`,
and `12,282 MiB` total VRAM.  `nvidia-smi` samples were `1,957 MiB` before
training, `4,290–4,358 MiB` during sampled training (maximum observed
`4,358 MiB`), and `1,833 MiB` after trainer shutdown.  No out-of-memory event
occurred.

The run used Isaac Sim `6.0.1` pre-built binaries through the bundled Python
`3.12.13`, PyTorch `2.10.0+cu128` (`torch.version.cuda = 12.8`, CUDA available),
Isaac Lab source commit `418ca31b47a8eb27db8aefcfc134e4c4f1d2b6f3`, and
`rsl-rl-lib 5.0.1`.  Runtime package metadata reports `isaaclab` `6.1.14`,
while `isaaclab.__version__` is `6.1.16`; the imported package files remain
source-linked to the pinned checkout.

### Trained Evaluation

The selected checkpoint was evaluated deterministically on the same v1 task
distribution for `256` completed episodes.  The one-off evaluator used the
official task and RSL-RL inference path; its JSON summary is external at
`C:\Users\getch\AppData\Local\Temp\exp018-v1-eval-model999-seed42.json`.

| Metric | Trained PPO (`model_999.pt`) |
| --- | ---: |
| Completed episodes | 256 |
| Successes / success rate | 256 / 100.0% |
| Mean final XY error | 4.3505043 mm |
| Median final XY error | 4.4388042 mm |
| Mean maximum insertion depth | 73.5355400 mm |
| Median maximum insertion depth | 63.1597340 mm |
| Mean episode length | 20.0898438 policy steps |
| Mean episodic reward | 0.3410851093 |
| Vectorized policy steps | 95 |

The per-region results were `backward 42/42`, `center 62/62`, `forward 45/45`,
`left 65/65`, and `right 42/42`.  A second deterministic evaluation with the
same seed and checkpoint produced the same values and counts exactly; its
external summary is
`C:\Users\getch\AppData\Local\Temp\exp018-v1-eval-model999-seed42-repeat.json`.

### Random vs Trained

The already-recorded random baseline used the same v1 task distribution,
`64` environments, seed `42`, and normalized `uniform[-0.3, 0.3]` actions for
`128` completed episodes.

| Metric | Random v1 (`128` eps) | Trained PPO (`256` eps) |
| --- | ---: | ---: |
| Successes / success rate | 0 / 0.0% | 256 / 100.0% |
| Mean final XY error | 13.6548 mm | 4.3505 mm |
| Mean maximum insertion depth | 0.0000 mm | 73.5355 mm |
| Mean episode length | 239 steps | 20.0898 steps |
| Mean episodic reward | -0.0001485529 | 0.3410851093 |

The trained result is materially better on every frozen task metric, including
the explicit insertion-success condition; the different episode counts are
reported rather than pooled.

### Failure Analysis or Learning Evidence

The first external evaluation attempt stopped before rollout because passing
the raw RSL-RL config directly constructed `MLPModel` with an unsupported
`stochastic` keyword.  The evaluator was then aligned with the official
trainer's `handle_deprecated_rsl_rl_cfg` conversion.  A second debug attempt
reached rollout but exposed a CPU/CUDA telemetry-only error in the temporary
evaluator's final-depth aggregation; keeping the final-depth tensor on CUDA
fixed that evaluator issue.  No task, reward, observation, action, or PPO
configuration was changed for either correction.

The 1,000-iteration run itself completed without an OOM or runtime exception.
Its non-fatal warnings remain in the external log: the missing pre-built-binary
`_isaac_sim\setup_conda_env.bat` wrapper notice, the Windows `libcarb.so`
Fabric logging/cp949 traceback, optional `isaaclab_visualizers` configuration,
MaterialX, PhysX TGS noisy-velocity, repeated disjointed `ee_joint` transform,
and RSL-RL `obs_groups` actor/critic fallback warnings.  They did not stop
training or evaluation.

The converged success signal, insertion depth, shorter episodes, lower XY
error, exact repeat evaluation, and all five sampled hole-position regions
support the classification `LEARNING_ESTABLISHED` for this frozen v1 task and
seed.  This does not establish robustness to a new seed or distribution.

### GUI Playback

The selected checkpoint was replayed through the native Learning Lab Kit UI
with one environment, randomized reset holes, and mode `TRAINED PPO` for
`900` steps.  The external summary is
`C:\Users\getch\AppData\Local\Temp\exp018-v1-gui-playback-long.json`;
the video is
`C:\Users\getch\AppData\Local\Temp\exp018-v1-gui-playback-long\rl-video-step-0.mp4`
(`1280 × 720`, `30 fps`, `900` frames, `30 s`).  The run observed `42` resets
with varied target offsets.  Inspected captures include:

- `C:\Users\getch\AppData\Local\Temp\exp018-v1-gui-playback-long\desktop-ui-trained-1.png` (`[-9.55, -16.82]` mm)
- `C:\Users\getch\AppData\Local\Temp\exp018-v1-gui-playback-long\desktop-ui-trained-2.png` (`[+2.92, -17.35]` mm)
- `C:\Users\getch\AppData\Local\Temp\exp018-v1-gui-playback-long\desktop-ui-trained-3.png` (`[-9.63, +21.21]` mm)

The UI showed the same trained policy responding after different randomized
hole resets; the aggregate result above is the quantitative claim.

### Parallel Visual

A short `9`-environment Kit preview used the same trained checkpoint for
`120` steps with independent randomized holes.  It exited `0`; the external
video is
`C:\Users\getch\AppData\Local\Temp\exp018-v1-parallel-playback-correct\rl-video-step-0.mp4`
(`1280 × 720`, `30 fps`, `120` frames, `4 s`) and the inspected desktop frame is
`C:\Users\getch\AppData\Local\Temp\exp018-v1-parallel-playback-correct\desktop-parallel-1.png`.
The preview showed nine UR10e instances and the UI mode `TRAINED PPO`; its
JSON contains distinct offsets for all nine environments.

### Repository Update

Only this existing `README.md` is changed to record the measured baseline.
The generated checkpoints, TensorBoard event file, logs, videos, screenshots,
temporary evaluator/playback scripts, caches, root dependencies,
`src/robotics_rnd`, and Isaac Lab checkout remain outside the tracked change.

### Classification

`LEARNING_ESTABLISHED`

### Next Best Action

The seed-43 in-distribution hold-out is recorded below.  Keep the task and PPO
configuration frozen before deciding whether a further hold-out seed is needed.

## Hold-Out Evaluation — Seed 43

### Protocol

The seed-42-trained checkpoint and all v1 task/PPO values were held fixed.  The
same temporary evaluator and deterministic RSL-RL inference path were invoked
with only the evaluation seed changed to `43`:

```powershell
$log = 'C:\Users\getch\AppData\Local\Temp\exp018-v1-eval-model999-seed43.log'
$output = 'C:\Users\getch\AppData\Local\Temp\exp018-v1-eval-model999-seed43.json'
$script = 'C:\Users\getch\AppData\Local\Temp\exp018_eval_seed42.py'
$checkpoint = 'C:\dev\IsaacLab\logs\rsl_rl\ur10e_peg_insert_learning\2026-08-28_02-40-31_exp018_v1_baseline_seed42\model_999.pt'
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p $script `
  --task Isaac-UR10e-PegInsert-Learning-v1 `
  --checkpoint $checkpoint `
  --num_envs 64 `
  --episodes 256 `
  --seed 43 `
  --output $output `
  --headless `
  --device cuda:0 *> $log
```

The command exited `0` with wrapper wall time `26.299 s` and evaluator rollout
time `5.7328925 s`.  The checkpoint SHA-256 remained
`D5D9AED8CA05D6BF5A9E64357BE146DD8E10782646ADEDC3E255A962CCF7CFAF`.

### Hold-Out Metrics

The external JSON summary is
`C:\Users\getch\AppData\Local\Temp\exp018-v1-eval-model999-seed43.json`.

| Metric | Seed-43 hold-out |
| --- | ---: |
| Completed episodes | 256 |
| Successes / success rate | 256 / 100.0% |
| Mean final XY error | 4.3389672 mm |
| Median final XY error | 4.3763618 mm |
| Mean maximum insertion depth | 75.4934595 mm |
| Median maximum insertion depth | 63.3184016 mm |
| Mean episode length | 20.8867188 policy steps |
| Mean episodic reward | 0.3412652672 |
| Vectorized policy steps | 97 |

### Region Results

| Region | Successes / episodes | Success rate |
| --- | ---: | ---: |
| Center | 50 / 50 | 100.0% |
| Left | 60 / 60 | 100.0% |
| Right | 40 / 40 | 100.0% |
| Forward | 56 / 56 | 100.0% |
| Backward | 50 / 50 | 100.0% |

### Seed 42 vs Seed 43

| Metric | Seed-42 trained eval | Seed-43 hold-out |
| --- | ---: | ---: |
| Successes / success rate | 256 / 100.0% | 256 / 100.0% |
| Mean final XY error | 4.3505 mm | 4.3390 mm |
| Mean maximum insertion depth | 73.5355 mm | 75.4935 mm |
| Mean episode length | 20.0898 steps | 20.8867 steps |
| Mean episodic reward | 0.3410851 | 0.3412653 |

The seed-43 reset sequence remains within the same frozen v1 distribution and
was not used for training.  This supports in-distribution hold-out behavior;
it is not an out-of-distribution, sim-to-real, physical, or training-seed
reproducibility claim.

### Random vs Trained

| Metric | Random v1 | Trained seed-42 eval | Hold-out seed-43 eval |
| --- | ---: | ---: | ---: |
| Successes / success rate | 0 / 128 (0.0%) | 256 / 256 (100.0%) | 256 / 256 (100.0%) |
| Mean final XY error | 13.6548 mm | 4.3505 mm | 4.3390 mm |
| Mean maximum insertion depth | 0.0000 mm | 73.5355 mm | 75.4935 mm |
| Mean episode length | 239 steps | 20.0898 steps | 20.8867 steps |
| Mean episodic reward | -0.0001485529 | 0.3410851 | 0.3412653 |

Raw success counts are retained; the three evaluations are not averaged.

### GUI Check

After the quantitative hold-out passed, the same checkpoint was replayed with
seed `43`, one environment, the existing Learning Lab UI, and mode
`TRAINED PPO` for `360` steps.  The run exited `0`, observed multiple
randomized reset offsets, and produced a `1280 × 720`, `30 fps`, `360`-frame
(`12 s`) video:

- JSON: `C:\Users\getch\AppData\Local\Temp\exp018-v1-gui-playback-seed43.json`
- Video: `C:\Users\getch\AppData\Local\Temp\exp018-v1-gui-playback-seed43\rl-video-step-0.mp4`
- Inspected desktop captures: `C:\Users\getch\AppData\Local\Temp\exp018-v1-gui-playback-seed43\desktop-seed43-2.png` and `C:\Users\getch\AppData\Local\Temp\exp018-v1-gui-playback-seed43\desktop-seed43-3.png`

The GUI check is visual playback evidence only; the aggregate success claim is
from the 256-episode evaluator above.

### Classification

`LEARNING_ESTABLISHED`
`IN_DISTRIBUTION_HOLDOUT_VERIFIED`

## Files changed

The v1 change is intentionally limited to the existing canonical Experiment
018 files:

- `README.md` — active v1 contract, v0 historical evidence, and measured v1 evidence;
- `registration.py` — v1 IDs, primitive plate/socket scene, and unchanged manager/PPO configuration;
- `learning_lab.py` — per-environment runtime hole state, socket pose writes, reset sampling, UI fields, and probe reporting.

No generated logs, checkpoints, TensorBoard events, videos, caches, root
dependencies, reusable-platform modules, Isaac Lab files, or helper scripts are
tracked.
