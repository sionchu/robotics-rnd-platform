# Experiment 020 — UR10e State-Only 3 mm Precision Learning

## Question

Can a freshly initialized, state-only PPO policy solve the `46 mm` square-hole
task with `3 mm` side clearance without force or contact observations?

The experiment is an external Isaac Lab task.  It does not modify the reusable
robotics platform, Isaac Lab, Experiment 018, or Experiment 019.

## Branch and external baseline

- Git branch: `exp/020-ur10e-state-precision`
- Isaac Lab checkout: `C:\dev\IsaacLab`
- Isaac Lab commit: `418ca31b47a8eb27db8aefcfc134e4c4f1d2b6f3`
- Isaac Sim: `C:\isaacsim`, `6.0.1-rc.7+release.42383.32955d8d.gl`
- Python: `C:\dev\IsaacLab\_isaac_sim\kit\python\python.exe`, `3.12.13`
- PyTorch: `2.10.0+cu128`; CUDA available; torch CUDA `12.8`
- RSL-RL: `rsl-rl-lib 5.0.1`
- GPU: NVIDIA GeForce RTX 4070 Ti, driver `591.86`

The Isaac Sim bundled Python is used through `isaaclab.bat`; no uv, conda, or
virtual environment is used for simulation.

## Task contract

The registered task IDs are:

- `Isaac-UR10e-PegInsert-StatePrecision-v1`
- `Isaac-UR10e-PegInsert-StatePrecision-Play-v1`

The task reuses the Experiment 018 manager environment and runtime machinery
through imports.  Experiment 020 changes only the four wall dimensions/poses,
the aperture constant, and the geometrically consistent success tolerance.

| Item | Experiment 020 |
| --- | --- |
| Peg | `40 × 40 mm`, `120 mm` long |
| Hole | `46 × 46 mm` |
| Side clearance | `3 mm` (`6 mm` total width difference) |
| Success lateral tolerance | Euclidean XY `≤ 3 mm` |
| Insertion success | depth `≥ 60 mm` |
| Reset hole range | X `±40 mm`, Y `±30 mm` |
| Initial peg XY error | `±15 mm` |
| Observation | `3 + 3 + 3 + 1 = 10` state values |
| Action | relative Cartesian `ΔXYZ`, dimension `3` |
| Action scale | `0.005 m` |
| IK | differential IK, relative mode, DLS `lambda=0.02` |
| Policy inputs | no force, torque, contact flag, camera, absolute hole pose, or orientation error |
| Reward | alignment `2.0`, gated insertion `3.0`, success bonus `10.0` |
| Timing | PhysX, `dt=1/60 s`, decimation `2`, policy step `1/30 s`, timeout `8 s` |

The four observation terms are `peg_pos_rel_hole (3)`,
`peg_linear_velocity (3)`, `previous_action (3)`, and `insertion_depth (1)`.

## Verification gates

`prekit_check.py` passed with the exact task IDs, 46/3 geometry, 10-value
observation contract, 3-action DLS controller, and PPO values.  The finite GUI
probe passed for 120 steps in one environment.  Its overlay was:
`EXPERIMENT 020 | STATE-ONLY PPO`, `Hole: 46 mm | Clearance: 3 mm | Success
XY: 3 mm`, `Observation: 10 state values | Action: ΔXYZ (3)`.

The 64-environment runtime gate passed for 30 vector steps with finite policy
observations and actions (`[64, 10]` and `[64, 3]`).

The deterministic insertion-oracle process ran to completion, but the fixed
state-only diagnostic did not reach the 60 mm insertion criterion (nominal
multi-environment probe: `0/9` successes, about `46.1 mm` maximum depth and
about `3.5 mm` final XY error).  This is a preserved diagnostic limitation,
not a claim that an oracle solved the task.

## Random baseline

Command: `evaluate.py --mode random --num_envs 64 --episodes 128 --seed 42`
with normalized actions sampled from `U[-0.3, +0.3]`.

| Metric | Result |
| --- | ---: |
| Episodes | 128 |
| Successes | 0 |
| Success rate | 0.0% |
| Mean final XY error | 13.8787 mm |
| Median final XY error | 13.4832 mm |
| Mean/median maximum insertion | 0.0000 / 0.0000 mm |
| Mean episode length | 239 policy steps |
| Mean episodic reward | -0.000142910 |

All 128 episodes timed out.  The regional counts were backward 28, center 24,
forward 22, left 33, and right 21; each region had `0` successes.

## PPO pipeline smoke

The five-iteration smoke used 64 environments, 24 steps per environment,
seed 42, headless PhysX, RSL-RL, and TensorBoard.  It produced
`64 × 24 × 5 = 7,680` transitions and `model_0.pt`/`model_4.pt`.

The TensorBoard tags emitted were:

`Episode_Reward/alignment_progress`, `Episode_Reward/insertion_progress`,
`Episode_Reward/success_bonus`, `Episode_Termination/success`,
`Episode_Termination/time_out`, `Loss/value`, `Loss/surrogate`,
`Loss/entropy`, `Loss/learning_rate`, `Policy/mean_std`, `Perf/total_fps`,
`Perf/collection_time`, `Perf/learning_time`, `Train/mean_reward`,
`Train/mean_episode_length`, `Train/mean_reward/time`, and
`Train/mean_episode_length/time`.

Smoke values over iterations 0→4 were:

| Metric | Iteration 0 | Iteration 4 |
| --- | ---: | ---: |
| Mean reward | -0.000228 | -0.001174 |
| Mean episode length | 14.77 | 47.00 |
| Success termination | 0.0 | 0.0 |
| Insertion reward | 0.0 | 0.0 |
| Policy mean std | 1.0088 | 1.0129 |

## 1,000-iteration training

The full run was from a fresh policy state, not Experiment 018 weights:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat train --rl_library rsl_rl --task Isaac-UR10e-PegInsert-StatePrecision-v1 --num_envs 64 --max_iterations 1000 --seed 42 --viz none --logger tensorboard --run_name exp020_state_precision_seed42 --device cuda:0 --external_callback experiments.robot.020_ur10e_peg_in_hole_state_precision.registration.register_tasks
```

The command exited `0`, emitted `1,536,000` transitions, and reported
`Training time: 961.87 seconds` (PowerShell wall time about `974 s`).  The run
directory is external:

`C:\dev\IsaacLab\logs\rsl_rl\ur10e_state_precision\2026-08-28_17-43-39_exp020_state_precision_seed42`

Selected TensorBoard values at iterations 0, 100, 250, 500, 750, and 999:

| Iteration | Mean reward | Mean episode length | Alignment reward | Insertion reward | Success bonus | Success | Timeout |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | -0.0002276 | 14.7692 | -0.0000519 | 0 | 0 | 0 | 0.0866 |
| 100 | 0.0004975 | 239 | 0.0000720 | 0 | 0 | 0 | 1 |
| 250 | 0.0001220 | 239 | 0.0000074 | 0 | 0 | 0 | 1 |
| 500 | 0.0006183 | 239 | 0.0000913 | 0 | 0 | 0 | 1 |
| 750 | 0.0006414 | 239 | 0.0001027 | 0 | 0 | 0 | 1 |
| 999 | 0.0006347 | 239 | 0.0000986 | 0 | 0 | 0 | 1 |

The policy standard deviation fell from `1.0088` to `0.1467`.  Value loss fell
from `0.0066048` to `3.82e-09`; the adaptive learning rate ended at `1e-5`.
No success or insertion reward was emitted during training.

## Checkpoint

Final checkpoint:

`C:\dev\IsaacLab\logs\rsl_rl\ur10e_state_precision\2026-08-28_17-43-39_exp020_state_precision_seed42\model_999.pt`

SHA-256:

`6C01FBFD1F7651072855ADEA67117A661619BBE58B7B724AA9433BCCC11B1A07`

## Paired 256 evaluation

The paired evaluation used the Experiment 019 plan unchanged:

- plan seed `43`
- plan SHA-256 `ece1662c6b5de3016c77b67c667b75f37551b3de80eaf137897645576abd2f2c`
- 64 environments × 4 episodes = 256
- deterministic inference
- exact IDs `env_00_ep_00` through `env_63_ep_03`

The evaluation command exited `0`; every environment consumed exactly four
planned episodes.

| Metric | Frozen Experiment 018 at 46 mm | Experiment 020 at 46 mm |
| --- | ---: | ---: |
| Success | 219 / 256 (85.5469%) | 0 / 256 (0.0%) |
| Mean final XY error | 2.9876 mm | 0.9813 mm |
| Median final XY error | not retained in this comparison source | 0.9650 mm |
| Mean maximum insertion | 109.1742 mm | 0.0000 mm |
| Median maximum insertion | not retained in this comparison source | 0.0000 mm |
| Mean episode length | 71.8164 steps | 239.0000 steps |
| Mean episodic reward | source baseline retained in Experiment 019 | 0.000595925 |

Experiment 020 recorded `256` timeouts and no contact-positive episodes.  The
mean XY error is lower than the old policy because the new policy learned to
align and then stopped descending; it is not a task success.

## Known 34-failure recovery

The comparison script validates all three paired files against the plan SHA
and episode IDs, then records old/new success, XY error, insertion depth, and
episode length for every ID.  For the pre-declared subset that was a 50 mm
success and a 46 mm failure under Experiment 018:

| Subset | Episodes | Recovered | Still failed | Mean XY error | Mean max insertion | Mean length |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen Experiment 018 at 46 mm | 34 | 0 | 34 | 4.2526 mm | 49.3977 mm | 239 |
| Experiment 020 at 46 mm | 34 | 0 | 34 | 0.8926 mm | 0.0000 mm | 239 |

The full per-episode JSON comparison is external at
`C:\Users\getch\AppData\Local\Temp\exp020-paired-comparison.json`.

## Hold-out seed 44

An independent deterministic evaluation used seed `44`, 256 completed
episodes, and the same 46 mm/3 mm task.  It exited `0`:

| Metric | Result |
| --- | ---: |
| Success | 0 / 256 (0.0%) |
| Mean / median final XY error | 0.9424 / 0.9403 mm |
| Mean / median maximum insertion | 0.0000 / 0.0000 mm |
| Mean episode length | 239 steps |
| Mean episodic reward | 0.000617066 |
| Timeouts | 256 |

Region counts were backward `51`, center `67`, forward `34`, left `58`, and
right `46`; all regions had zero successes.

## Classification

`STATE_PRECISION_LEARNING_NOT_ESTABLISHED`

The run establishes that the 10-value state-only policy can reduce XY error,
but it did not discover the insertion phase: all training and evaluation
episodes timed out before any measurable insertion.  The single next
bottleneck is insertion exploration/credit assignment under the unchanged
gated reward and 3 mm aperture.  This result does not establish that force or
contact observations are required; that is a separate experiment boundary.

The optional nine-environment promotional visual and a paired GUI replay were
not run because the pre-declared learning condition was not met.  The finite
GUI task probe remains available in `gui_probe.py`.

## External evidence and warnings

Generated checkpoints, TensorBoard event files, videos, caches, and JSON
results remain outside Git.  Runtime logs repeatedly reported the existing
Isaac Sim/PhysX warnings: missing `_isaac_sim\setup_conda_env.bat`, Linux-only
`libcarb.so` Fabric notice with a Windows CP949 logging error, missing
`isaaclab_visualizers` extension config, MaterialX/Fabric notices, TGS noisy
velocity, duplicate warp, and disjointed `ee_joint` transform warnings.  They
did not change the exit status of the finite runs or the 1,000-iteration run.

The first full-training invocation without the repository `PYTHONPATH` failed
at import with `ModuleNotFoundError: No module named 'experiments'`; the
official command above was rerun with the required path and is the run used
for all metrics.
