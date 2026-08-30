# Experiment 022 — UR10e Success-Aligned Axial Credit

## Question

Does restricting axial-progress credit to the actual 3 mm lateral success
region improve state-only alignment/descent coordination?

## Controlled variable

Experiment 021 rewards signed axial progress while XY error is at most 10 mm.
Experiment 022 changes only that predicate to the task-local 3 mm success
tolerance:

```text
r_axial = 1[xy_error <= SUCCESS_LATERAL_M] * axial_progress
SUCCESS_LATERAL_M = 0.003 m
```

The signed progress equation, shared `_tracker_valid` lifecycle, term order,
weights, task geometry, success conditions, observation/action contracts,
controller, resets, episode horizon, and PPO configuration remain frozen.

## Frozen task contract

- peg / hole: 40 mm / 46 mm square, 3 mm side clearance
- success: XY error at most 3 mm and insertion depth at least 60 mm
- observation: 10 state values; no force, contact, camera, or vision input
- action: three-dimensional relative Cartesian position, scale 0.005 m
- controller: Differential IK, DLS lambda 0.02, fixed orientation
- reset: hole X +/-40 mm, hole Y +/-30 mm, peg-relative XY +/-15 mm,
  approach height 25 mm
- episode: 8 seconds, 30 Hz control, 240 configured steps
- PPO: seed 42, 64 environments, 24 steps per environment, 1000 iterations,
  actor/critic `[64, 64]`, ELU, initial standard deviation 1.0, adaptive
  learning rate 0.001, gamma 0.99, lambda 0.95, clip 0.2, entropy 0.001,
  desired KL 0.01, CUDA and PhysX

## Reward contract

The manager order and weights are:

1. `alignment_progress`, weight `2.0`
2. `success_aligned_axial_progress`, weight `3.0`
3. `success_bonus`, weight `10.0`

## Predeclared classification

`SUCCESS_ALIGNED_AXIAL_CREDIT_ESTABLISHED` requires all of:

- paired success at least `216 / 256`;
- hold-out seed-44 success at least `205 / 256`;
- paired net recovery at least `13`, where net recovery is Experiment 021
  failure to 022 success minus Experiment 021 success to 022 failure;
- `DEPTH_NOT_REACHED + LOST_ALIGNMENT_DURING_INSERTION <= 34`; and
- `ALIGNMENT_NOT_REACHED <= 14`.

Otherwise the result is
`SUCCESS_ALIGNED_AXIAL_CREDIT_NOT_ESTABLISHED`. These thresholds were frozen
before training or evaluating Experiment 022.

## Evidence

### Pre-Kit and runtime verification

The pre-Kit registration/configuration check exited `0`. It confirmed both
task IDs, the 40/46 mm geometry, 3/60 mm success thresholds, 8-second horizon,
60 Hz simulation with decimation 2, 10 observations, three actions, relative
Cartesian position control at scale 0.005, DLS lambda 0.02, the exact reward
order/weights above, and the frozen PPO configuration.

The native single-environment Kit view was then run for 180 finite steps and
inspected directly. It showed the UR10e, randomized plate/hole, 10-D policy to
three-dimensional Cartesian action pipeline, and the existing Learning UI with
the Experiment 022 title and 3 mm axial-gate label. The runtime observation
space was `Dict(policy: (1, 10))`, the action space was `(1, 3)`, and the first
and final observations were finite. The PowerShell `Tee-Object` wrapper used
for that GUI run did not return after Simulation App shutdown and was manually
interrupted; the Python probe itself had already written its finite 180-step
JSON. Subsequent headless commands avoided that wrapper and exited normally.

### Controlled equivalence and reward semantics

Experiment 021 and Experiment 022 were run in separate fresh processes with
seed 42, the same initial condition, and the same 72-step deterministic action
sequence. The maximum absolute differences were all exactly `0.0` for actions,
observations, XY error, peg Z, insertion depth, alignment reward, and success
reward. The trajectory contained 28 steps above 10 mm, eight steps in the
3--10 mm band, and 36 steps at or below 3 mm.

Representative semantic checks were:

| Step | XY error | Z action | Experiment 021 axial | Experiment 022 axial |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 13.5165 mm | -0.35 | 0 | 0 |
| 29 | 9.9687 mm | -0.35 | +0.00273773 | 0 |
| 37 | 2.8136 mm | -0.35 | +0.00008672 | +0.00008672 |
| 60 | 0.3812 mm | +0.30 | -0.00007537 | -0.00007537 |

The unchanged alignment reward was active in both directions: deliberate XY
improvement produced `+0.00578874`, while deliberate worsening produced
`-0.00265355`. These results establish that the only observed intentional
difference is axial credit during physical progress in the 3--10 mm band.

### Random-policy baseline

The seed-42 random policy used 64 environments and actions sampled from
`U[-0.3, +0.3]` until 128 episodes completed. It exited `0` in 15.999 seconds:

- success: `0 / 128`; timeouts: `128 / 128`;
- mean / median final XY error: `13.8787 / 13.4832 mm`;
- mean maximum insertion depth: `0 mm`;
- mean episode length: `239` steps;
- mean episodic reward: `-0.00013857`;
- mean alignment / axial reward: `-0.00014291 / +0.00000434`.

### PPO pipeline smoke

The five-iteration smoke used the frozen seed-42 configuration and command:

```powershell
.\isaaclab.bat train --rl_library rsl_rl `
  --task Isaac-UR10e-PegInsert-SuccessAlignedAxial-v1 `
  --num_envs 64 --max_iterations 5 --seed 42 --headless `
  --logger tensorboard --run_name exp022_success_aligned_smoke_seed42 `
  --device cuda:0 --deterministic `
  --external_callback experiments.robot.022_ur10e_peg_in_hole_success_aligned_axial.registration.register_tasks
```

It exited `0`, processed 7,680 transitions in 8.62 seconds, and created
`model_0.pt` and `model_4.pt`. TensorBoard emitted finite alignment, axial,
success, termination, loss, learning-rate, entropy, standard-deviation, reward,
and episode-length series. At iteration 4, alignment reward was
`-0.00033256`, axial reward was `+0.00000051`, policy standard deviation was
`1.01309`, and success was zero. This run verifies only the PPO pipeline.

### Full training

The full run changed only `--max_iterations 1000` and the run name to
`exp022_success_aligned_seed42`. It trained from scratch, exited `0`, and
processed exactly `64 * 24 * 1000 = 1,536,000` transitions in 1,326.85
seconds. The observed GPU allocation during monitoring was approximately
3.26--3.38 GiB; this is an observed range, not a continuously sampled peak.

Selected TensorBoard samples are:

| Iteration | Mean reward | Mean length | Alignment | Axial | Success | Timeout | Policy std |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | -0.000228 | 14.77 | -0.0000519 | 0 | 0 | 0.0866 | 1.0083 |
| 100 | 0.008191 | 238.51 | 0.0000522 | 0.0005563 | 0 | 1.0 | 0.5166 |
| 250 | 0.005779 | 239 | 0.0000302 | 0.0007652 | 0 | 1.0 | 0.2591 |
| 500 | 0.006757 | 239 | 0.0000739 | 0.0007506 | 0 | 1.0 | 0.1733 |
| 750 | 0.006777 | 239 | 0.0000880 | 0.0007907 | 0 | 1.0 | 0.1535 |
| 999 | 0.006737 | 239 | 0.0000817 | 0.0007339 | 0 | 1.0 | 0.1475 |

Axial reward first became nonzero at iteration 2. Using an analysis reporting
threshold of absolute reward at least `1e-4`, it first became meaningfully
nonzero at iteration 47 (`-0.00010509`). A transient nonzero success event was
first logged at iteration 87 (`0.009765625`), but success was zero at all six
selected samples and at iteration 999. The reporting threshold is not part of
the task or reward definition.

The final checkpoint is external at:

```text
C:\dev\IsaacLab\logs\rsl_rl\ur10e_success_aligned_axial\
2026-08-31_01-59-33_exp022_success_aligned_seed42\model_999.pt
```

SHA-256:

```text
367171F8E7A2D9C3EDE3D3CD127B3FC8C989D58A25C9D07342A31319218AE11F
```

### Paired evaluation

The final checkpoint was evaluated deterministically on the exact Experiment
019 paired reset plan (`64` environments, four episodes per environment,
256 stable IDs, seed 43):

```text
plan SHA-256: ece1662c6b5de3016c77b67c667b75f37551b3de80eaf137897645576abd2f2c
```

Results:

- success: `0 / 256` (`0%`); timeouts: `256 / 256`;
- mean / median final XY error: `3.2241 / 3.2237 mm`;
- mean / median maximum insertion depth: `46.9614 / 46.9577 mm`;
- mean episode length: `239` steps;
- mean episodic reward: `0.0067783`;
- mean / median / maximum wrist-contact diagnostic:
  `9.4196 / 9.4463 / 21.6685 N`.

The exact per-ID transition matrix from corrected Experiment 021 to
Experiment 022 is:

| Transition | Episodes |
| --- | ---: |
| 021 success -> 022 success | 0 |
| 021 success -> 022 failure | 203 |
| 021 failure -> 022 success | 0 |
| 021 failure -> 022 failure | 53 |

Net recovery is therefore `0 - 203 = -203`.

All 256 Experiment 022 failures are `DEPTH_NOT_REACHED`. Every episode entered
XY at or below 3 mm (first entry mean / median step `8.28 / 7`, range `1--18`),
but none reached 60 mm insertion and none met both success conditions. No
episode is classified as `ALIGNMENT_NOT_REACHED`,
`LOST_ALIGNMENT_DURING_INSERTION`, or `COORDINATION_MISS`.

For those 256 failures:

- minimum XY error mean / median: `0.4166 / 0.4619 mm`;
- time inside 3 mm: mean / median `53.21 / 53` steps, range `39--66`;
- time in the 3--10 mm band: mean / median `184.63 / 185` steps,
  range `171--198`;
- positive insertion gain while inside 3 mm: mean / median
  `46.0497 / 46.0616 mm`;
- positive insertion gain while outside 3 mm: mean / median
  `0.9324 / 0.9453 mm`;
- maximum insertion depth range: `45.4114--48.7520 mm`.

Insertion gain is the sum of positive per-step insertion-depth increments;
negative reversals are not subtracted. The telemetry shows that the policy did
discover precise alignment and substantial gated descent, then converged to a
repeatable state just outside the 3 mm gate and about 13 mm short of the 60 mm
success depth.

### Hold-out seed 44

The normal deterministic hold-out evaluation completed 256 episodes:

- success: `0 / 256` (`0%`); timeouts: `256 / 256`;
- mean / median final XY error: `3.2243 / 3.2235 mm`;
- mean / median maximum insertion depth: `46.9472 / 46.9400 mm`;
- mean episode length: `239` steps;
- mean episodic reward: `0.00675265`;
- regions: backward `0/51`, center `0/67`, forward `0/34`, left `0/58`,
  right `0/46`.

### Classification

The predeclared result is:

```text
SUCCESS_ALIGNED_AXIAL_CREDIT_NOT_ESTABLISHED
```

The paired success (`0 < 216`), hold-out success (`0 < 205`), net recovery
(`-203 < 13`), and combined depth/lost-alignment failures (`256 > 34`) all
fail their frozen thresholds. Only the alignment-failure ceiling passes
(`0 <= 14`). The result supports the predeclared exploration-risk concern:
the 3 mm axial gate changed the learned coordination regime, but it did not
establish a better task policy. It does not show that the existing 10 mm gate
caused Experiment 021's failures, and it does not justify changing rewards,
PPO, force/contact inputs, geometry, or controller within this experiment.

Generated logs, TensorBoard events, JSON, checkpoints, GUI output, and caches
remain external and untracked.

### Runtime warnings

Runs repeatedly emitted non-fatal warnings for the absent
`setup_conda_env.bat` in the pre-built-binary workflow, deprecated
`--headless`, a Linux-only `libcarb.so` lookup followed by CP949 logging errors,
the absent `isaaclab_visualizers` extension config, MaterialX, TGS noisy
velocities, disjoint `ee_joint` transforms, and RSL-RL policy observation-group
fallback. No CUDA out-of-memory, NaN, task exception, or failed headless exit
occurred. A direct bundled-Python TensorBoard reader initially lacked the
Isaac Lab environment path and raised `ModuleNotFoundError: numpy`; rerunning
the same reader through `isaaclab.bat -p` exited `0`.
