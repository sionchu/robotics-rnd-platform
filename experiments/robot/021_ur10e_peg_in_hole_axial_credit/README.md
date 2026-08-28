# Experiment 021 — UR10e State-Only Axial Credit Learning

## Question

Can a freshly initialized state-only PPO policy solve the `46 mm` square-hole
task with `3 mm` side clearance when the insertion-progress reward is replaced
by continuous, gated axial progress?

This is a controlled follow-up to Experiments 018–020.  It does not modify
those experiments, the reusable robotics platform, Isaac Lab, or Isaac Sim.
The only experimental variable is the task reward topology.

## Branch and external baseline

- Git branch: `exp/021-ur10e-axial-credit`
- Research parent: Experiment 020 HEAD `8f2a5ef5fde7675a39335cd120c52a40bf3bc309`
- Preserved first-run evidence commit: `efae5981c7c61af1ec6cdca9c56288d040971431`
- Isaac Lab checkout: `C:\dev\IsaacLab`
- Isaac Lab commit: `418ca31b47a8eb27db8aefcfc134e4c4f1d2b6f3`
- Isaac Sim: `C:\isaacsim`, `6.0.1-rc.7+release.42383.32955d8d.gl`
- Python: `C:\dev\IsaacLab\_isaac_sim\kit\python\python.exe`, `3.12.13`
- PyTorch: `2.10.0+cu128`; CUDA available; torch CUDA `12.8`
- RSL-RL: `rsl-rl-lib 5.0.1`
- GPU: NVIDIA GeForce RTX 4070 Ti, driver `591.86`

Isaac Sim's bundled Python is used through `isaaclab.bat`.  No uv, conda,
virtual environment, second Isaac Sim installation, or WSL fallback is used
for the simulation runs.

## Task contract

The registered task IDs are:

- `Isaac-UR10e-PegInsert-AxialCredit-v1`
- `Isaac-UR10e-PegInsert-AxialCredit-Play-v1`

The task imports the canonical Experiment 018/020 scene, controller,
observation, reset, and success machinery.  The 021 files only register the
new task, implement the axial reward tracker, expose the two Learning UI
values, and provide finite evidence runners.

| Item | Experiment 021 |
| --- | --- |
| Peg | `40 × 40 mm`, `120 mm` long |
| Hole | `46 × 46 mm` |
| Side clearance | `3 mm` (`6 mm` total width difference) |
| Success lateral tolerance | Euclidean XY `≤ 3 mm` |
| Insertion success | depth `≥ 60 mm` |
| Reset hole range | X `±40 mm`, Y `±30 mm` |
| Initial peg XY error | `±15 mm` |
| Approach height | approximately `25 mm` above the hole top |
| Observation | `3 + 3 + 3 + 1 = 10` state values |
| Action | relative Cartesian `ΔXYZ`, dimension `3` |
| Action scale | `0.005 m` |
| IK | differential IK, relative mode, DLS `lambda=0.02` |
| Policy inputs | no force, torque, contact flag, camera, absolute hole pose, or orientation error |
| Timing | PhysX, `dt=1/60 s`, decimation `2`, policy step `1/30 s`, timeout `8 s` |

The four observation terms are `peg_pos_rel_hole (3)`,
`peg_linear_velocity (3)`, `previous_action (3)`, and `insertion_depth (1)`.

## Controlled reward variable

The reward manager still has exactly three conceptual terms:

| Term | Weight | Definition |
| --- | ---: | --- |
| `alignment_progress` | `2.0` | unchanged Experiment 020 alignment progress |
| `gated_axial_progress` | `3.0` | new signed axial progress |
| `success_bonus` | `10.0` | unchanged success bonus |

`insertion_progress` is absent.  In
`runtime.py`, the new term defines:

```text
success_target_z = hole_top_z - SUCCESS_DEPTH_M
axial_remaining = max(peg_tip_z - success_target_z, 0)
raw_progress = previous_axial_remaining - current_axial_remaining
r_axial = 1[XY error <= 10 mm] * raw_progress
```

The value is in meters, is positive for valid downward progress, negative for
upward motion, and becomes zero after the success-depth target is reached.  The
axial-remaining tracker is reset per environment, shares the canonical
validity lifecycle with alignment, and does not add a fourth reward term.

## Tracker coupling and controlled-comparison repair

The canonical Experiment 018 implementation was inspected before this repair
at `experiments/robot/018_ur10e_peg_in_hole/learning_lab.py`:

- `alignment_progress` reads `env._tracker_valid`, uses zero initial progress
  when it is false, and updates `_previous_xy_error`.
- `insertion_progress` reads the same validity flag, updates
  `_previous_insertion_depth`, and then sets `env._tracker_valid = True`.

The first 021 implementation replaced `insertion_progress` with an independent
`_axial_tracker_valid`.  Because the canonical alignment term still read
`_tracker_valid`, alignment progress stayed zero throughout that run.  The
first run is therefore a tracker-confounded control, not evidence that signed
axial credit failed.

The minimal repair in `runtime.py` makes `gated_axial_progress` use the
canonical `env._tracker_valid` lifecycle and set it true after its update.  The
redundant `_axial_tracker_valid` allocation/reset was removed; only
`_previous_axial_remaining` and `_last_reward_axial` remain for the new term.

Before retraining, an external 48-step deterministic comparison used the same
seed, reset, and action sequence for the Experiment 020 and repaired 021 tasks.
The policy observation shape was `[1, 10]` in both runs.  Maximum absolute
differences were zero for observations, actions, XY error, peg Z, insertion
depth, raw alignment progress, and weighted alignment reward.  Thus the
physical trajectory and unchanged alignment term matched step by step; only
`insertion_progress` versus `gated_axial_progress` differed.  The two external
traces are
`C:\Users\getch\AppData\Local\Temp\exp021-equivalence-020.json` and
`C:\Users\getch\AppData\Local\Temp\exp021-equivalence-021.json`.

The two task invocations were:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\Users\getch\AppData\Local\Temp\exp021_trackerfix_equivalence.py --task Isaac-UR10e-PegInsert-StatePrecision-v1 --output C:\Users\getch\AppData\Local\Temp\exp021-equivalence-020.json --headless --device cuda:0
.\isaaclab.bat -p C:\Users\getch\AppData\Local\Temp\exp021_trackerfix_equivalence.py --task Isaac-UR10e-PegInsert-AxialCredit-v1 --output C:\Users\getch\AppData\Local\Temp\exp021-equivalence-021.json --headless --device cuda:0
```

Both commands exited `0`.

## Pre-training gates

Command:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\021_ur10e_peg_in_hole_axial_credit\prekit_check.py
```

Exit status was `0`.  `prekit_check.py` passed with the two task IDs, 46/3 geometry, 10-value
observation contract, 3-action DLS controller, exactly three reward terms, and
the frozen PPO values.  The finite GUI probe also passed with one environment.

### First-run reward-credit probe (before tracker repair)

Command:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\021_ur10e_peg_in_hole_axial_credit\semantic_probe.py --task Isaac-UR10e-PegInsert-AxialCredit-v1 --steps 220 --seed 42 --output C:\Users\getch\AppData\Local\Temp\exp021-semantic-probe.json --headless --device cuda:0
```

Exit status was `0`.  The pre-repair probe ran 220 steps and demonstrated the
axial condition, but it did not establish an active unchanged alignment term:

- while above the hole top, `insertion_depth == 0` occurred;
- while still above the top and inside the `10 mm` XY gate, axial progress was
  positive.

The first positive record was step `23`: XY error `9.9516 mm`, Z error
`25.1280 mm`, axial remaining `85.1280 mm`, insertion depth `0 mm`, and axial
reward `+3.04878e-05`.  A negative above-gate value was also observed for an
upward motion.  These values remain evidence for the original axial formula;
the alignment tracker coupling was discovered afterward.

### Corrected reward semantic regression

Command (external output:
`C:\Users\getch\AppData\Local\Temp\exp021-trackerfix-semantic-probe-v2.json`):

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\021_ur10e_peg_in_hole_axial_credit\semantic_probe.py --task Isaac-UR10e-PegInsert-AxialCredit-v1 --steps 220 --seed 42 --output C:\Users\getch\AppData\Local\Temp\exp021-trackerfix-semantic-probe-v2.json --headless --device cuda:0
```

Exit status was `0`.  All four mandatory conditions were true:

- alignment reward became positive after initialization (first observed at
  step `2`, `+0.0021992943`) and negative during deliberate worsening (step
  `25`, `-0.0019365399`);
- above the hole top, `insertion_depth == 0` was observed;
- while above the top and inside the `10 mm` gate, axial progress was positive
  (step `6`, XY `3.6713 mm`, axial remaining `85.6463 mm`, insertion `0 mm`,
  axial reward `+0.0001881123`).

The same probe also recorded negative axial progress for upward motion.  This
time the rise phase was deliberately commanded: at step `50`, while still
above the top (`insertion 0 mm`, XY `1.1267 mm`), axial reward was
`-9.16421e-05`.  The required semantic regression flags were all true,
including `axial_negative_on_rise`.

### Pre-repair Native Learning UI probe

Command:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\021_ur10e_peg_in_hole_axial_credit\gui_probe.py --task Isaac-UR10e-PegInsert-AxialCredit-Play-v1 --steps 180 --seed 42 --output C:\Users\getch\AppData\Local\Temp\exp021-gui-probe.json --viz kit --device cuda:0
```

Exit status was `0`.  The pre-repair native Learning UI displayed the flow
`ALIGN ↓ AXIAL APPROACH ↓ INSERT ↓ SUCCESS`, `Axial Remaining: xx.x mm`, and
`Axial Progress Reward: +x.xxxx`.  The scripted probe crossed the hole top and
reported insertion depth.  This is a visualization/runtime check, not a claim
about the trained policy; its alignment value was not a valid controlled
comparison because the tracker coupling was still present.

### Corrected Native Learning UI regression

Command (external output:
`C:\Users\getch\AppData\Local\Temp\exp021-trackerfix-gui-probe-v2.json`):

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\021_ur10e_peg_in_hole_axial_credit\gui_probe.py --task Isaac-UR10e-PegInsert-AxialCredit-Play-v1 --steps 180 --seed 42 --output C:\Users\getch\AppData\Local\Temp\exp021-trackerfix-gui-probe-v2.json --viz kit --device cuda:0
```

Exit status was `0`.  The existing Learning UI ran 180 steps and its captured
labels and samples showed alignment reward, axial progress reward, XY error,
axial remaining, insertion depth, action, and total reward updating in the
same window.  The flow label remained
`ALIGN ↓ AXIAL APPROACH ↓ INSERT ↓ SUCCESS`; the scripted trajectory reached
`46.7897 mm` insertion.  No dashboard or new UI panel was added.

## First-run random baseline (preserved)

Command:

```powershell
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\021_ur10e_peg_in_hole_axial_credit\random_baseline.py --task Isaac-UR10e-PegInsert-AxialCredit-v1 --num_envs 64 --episodes 128 --seed 42 --output C:\Users\getch\AppData\Local\Temp\exp021-random-seed42.json --headless --device cuda:0
```

Exit status was `0`; 128 complete episodes were collected with normalized
actions sampled from `U[-0.3, +0.3]`.

| Metric | Random result |
| --- | ---: |
| Success | `0 / 128` (`0.0%`) |
| Mean final XY error | `13.8787 mm` |
| Median final XY error | `13.4832 mm` |
| Mean maximum insertion | `0.0000 mm` |
| Mean episode length | `239` policy steps |
| Mean episodic reward | `9.02030e-06` |
| Mean axial-progress reward | `9.02031e-06` |

All 128 episodes timed out.  Region counts were backward `28`, center `24`,
forward `22`, left `33`, and right `21`; every region had zero successes.
The runtime spaces in this 64-environment run were policy `[64, 10]` and
actions `[64, 3]`, with finite values and the reward terms
`alignment_progress`, `gated_axial_progress`, and `success_bonus`.

## Corrected random-baseline regression

The changed reward contract was rerun after the shared tracker repair with the
same 64 environments, seed `42`, `U[-0.3, +0.3]` actions, and 128 completed
episodes.  External output:
`C:\Users\getch\AppData\Local\Temp\exp021-trackerfix-random-seed42.json`.

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\021_ur10e_peg_in_hole_axial_credit\random_baseline.py --task Isaac-UR10e-PegInsert-AxialCredit-v1 --num_envs 64 --episodes 128 --seed 42 --output C:\Users\getch\AppData\Local\Temp\exp021-trackerfix-random-seed42.json --headless --device cuda:0
```

Exit status was `0`.  The corrected run again produced `0 / 128` successes;
all 128 episodes timed out.  Mean final XY error was `13.8787487 mm`, mean
maximum insertion was `0 mm`, mean episode length was `239` steps, mean
episodic reward was `9.0203045e-06`, and mean gated axial reward was
`9.0203054e-06`.  Region counts were backward `28`, center `24`, forward
`22`, left `33`, and right `21`, with zero successes in every region.  The
policy observation/action shapes were `[64, 10]` and `[64, 3]`.

## PPO five-iteration smoke

Command:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat train --rl_library rsl_rl --task Isaac-UR10e-PegInsert-AxialCredit-v1 --num_envs 64 --max_iterations 5 --seed 42 --headless --logger tensorboard --run_name exp021_smoke_seed42 --device cuda:0 --deterministic --external_callback experiments.robot.021_ur10e_peg_in_hole_axial_credit.registration.register_tasks
```

Exit status was `0`; `64 × 24 × 5 = 7,680` transitions were collected in
`5.86 s` of reported training time (PowerShell wall time about `19.4 s`).
The external run directory was
`C:\dev\IsaacLab\logs\rsl_rl\ur10e_axial_credit\2026-08-28_19-07-01_exp021_smoke_seed42`.
It contains `model_0.pt`, `model_4.pt`, and a TensorBoard event file.

| Metric | Iteration 0 | Iteration 4 |
| --- | ---: | ---: |
| Mean reward | `6.95068e-05` | `2.37966e-05` |
| Mean episode length | `14.7692` | `47.0` |
| Gated axial reward | `8.47972e-06` | `3.09842e-05` |
| Success termination | `0.0` | `0.0` |
| Timeout termination | `0.0866` | `0.5143` |
| Policy mean std | `1.00859` | `1.01293` |

TensorBoard emitted `Episode_Reward/alignment_progress`,
`Episode_Reward/gated_axial_progress`, `Episode_Reward/success_bonus`,
`Episode_Termination/success`, `Episode_Termination/time_out`,
`Loss/value`, `Loss/surrogate`, `Loss/entropy`, `Loss/learning_rate`,
`Policy/mean_std`, `Perf/total_fps`, `Perf/collection_time`,
`Perf/learning_time`, `Train/mean_reward`, and
`Train/mean_episode_length` (plus their time scalars).  The smoke only proves
the pipeline and checkpoint path; it does not demonstrate learning.

### Corrected tracker-fix smoke

Command:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat train --rl_library rsl_rl --task Isaac-UR10e-PegInsert-AxialCredit-v1 --num_envs 64 --max_iterations 5 --seed 42 --headless --logger tensorboard --run_name exp021_axial_credit_trackerfix_smoke_seed42 --device cuda:0 --deterministic --external_callback experiments.robot.021_ur10e_peg_in_hole_axial_credit.registration.register_tasks
```

Exit status was `0`; `64 × 24 × 5 = 7,680` transitions were collected in
`6.58 s` of reported training time (PowerShell wall time about `18.5 s`).  The
external run directory is
`C:\dev\IsaacLab\logs\rsl_rl\ur10e_axial_credit\2026-08-28_20-13-13_exp021_axial_credit_trackerfix_smoke_seed42`.
It contains `model_0.pt`, `model_4.pt`, and TensorBoard events.

| Metric | Iteration 0 | Iteration 4 |
| --- | ---: | ---: |
| Mean reward | `-0.0001580493` | `-0.0011465907` |
| Mean episode length | `14.7692` | `47.0` |
| Alignment reward | `-0.0000519364` | `-0.0003243623` |
| Gated axial reward | `0.0000084797` | `0.0000335001` |
| Success termination | `0.0` | `0.0` |
| Timeout termination | `0.0866` | `0.5143` |
| Policy mean std | `1.00875` | `1.01416` |

The corrected smoke TensorBoard emitted non-zero
`Episode_Reward/alignment_progress` and
`Episode_Reward/gated_axial_progress`, plus the same loss, performance,
termination, and policy tags listed above.  It verifies a finite rollout and
checkpoint creation only; it is not a learning claim.

## First 1,000-iteration training (invalidated control)

The run was from a fresh policy and used the unchanged Experiment 020 PPO
configuration:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat train --rl_library rsl_rl --task Isaac-UR10e-PegInsert-AxialCredit-v1 --num_envs 64 --max_iterations 1000 --seed 42 --headless --logger tensorboard --run_name exp021_axial_credit_seed42 --device cuda:0 --deterministic --external_callback experiments.robot.021_ur10e_peg_in_hole_axial_credit.registration.register_tasks
```

The log reached `Learning iteration 999/1000` and `Total steps: 1536000`, and
reported `Training time: 1071.25 seconds`.  The launcher wrapper did not return
a final PowerShell exit code in this session; the terminal log ended after
`SimulationContext cleared` and the expected checkpoints and event file are
present.  No out-of-memory or training exception was reported in the run log.

External run directory:

`C:\dev\IsaacLab\logs\rsl_rl\ur10e_axial_credit\2026-08-28_19-08-21_exp021_axial_credit_seed42`

The run contains checkpoints at the sampled iterations and `model_999.pt`.
The exact RSL-RL configuration is preserved in its external `params` files:
64 environments, 24 steps per environment, actor/critic `[64, 64]` with ELU,
initial std `1.0`, learning rate `0.001` adaptive, gamma `0.99`, lambda `0.95`,
clip `0.2`, entropy coefficient `0.001`, desired KL `0.01`, seed `42`, and
`cuda:0`.

## First-run learning curves (preserved evidence)

TensorBoard values sampled at iterations `0`, `100`, `250`, `500`, `750`, and
`999` were:

| Iteration | Mean reward | Episode length | Alignment | Axial progress | Success | Timeout | Policy std |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | `6.95068e-05` | `14.7692` | `0` | `8.47972e-06` | `0` | `0.0866` | `1.00859` |
| 100 | `-4.23974e-04` | `239` | `0` | `-7.43848e-05` | `0` | `1.0` | `0.411883` |
| 250 | `-8.32494e-04` | `239` | `0` | `-6.60487e-05` | `0` | `1.0` | `0.086016` |
| 500 | `-1.06940e-03` | `239` | `0` | `-3.38690e-05` | `0` | `1.0` | `0.034254` |
| 750 | `-6.46430e-04` | `239` | `0` | `-6.79110e-05` | `0` | `1.0` | `0.028008` |
| 999 | `-5.45337e-04` | `239` | `0` | `-1.33751e-05` | `0` | `1.0` | `0.023211` |

Value loss decreased from `0.00660880` to `6.21122e-09`; surrogate loss was
`-0.0138405` at iteration 0 and `-0.00957082` at 999; entropy loss moved from
`4.27167` to `-7.18515`; and the adaptive learning rate moved from `0.0015`
to `1e-5`.  The first sampled non-zero axial-progress record was iteration 0,
which is an initial random-rollout signal.  No success termination occurred at
any sampled point, so there is no first successful iteration.

The curve shows policy collapse to long timeouts, near-zero alignment reward,
signed axial reward near zero/negative, and policy standard deviation `0.0232`.
It does not show learned descent.

## Corrected 1,000-iteration training

After the equivalence and semantic gates passed, a fresh policy was trained
with the unchanged Experiment 020 PPO configuration.  The corrected run was
not initialized from either the invalid 021 checkpoint or Experiment 020.

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat train --rl_library rsl_rl --task Isaac-UR10e-PegInsert-AxialCredit-v1 --num_envs 64 --max_iterations 1000 --seed 42 --headless --logger tensorboard --run_name exp021_axial_credit_trackerfix_seed42 --device cuda:0 --deterministic --external_callback experiments.robot.021_ur10e_peg_in_hole_axial_credit.registration.register_tasks
```

Exit status was `0`.  The log reached `Learning iteration 999/1000`,
`Total steps: 1536000`, and reported `Training time: 1225.02 seconds`.
The external run directory is
`C:\dev\IsaacLab\logs\rsl_rl\ur10e_axial_credit\2026-08-28_20-14-38_exp021_axial_credit_trackerfix_seed42`.
The run has checkpoints through `model_999.pt` and a single TensorBoard event
file.  Its external log is
`C:\Users\getch\AppData\Local\Temp\exp021-trackerfix-ppo-seed42.log`.

The run parameters recorded in `params/agent.yaml` were seed `42`, device
`cuda:0`, 64 environments, 24 steps per environment, 1,000 iterations,
actor/critic `[64, 64]` with ELU, initial standard deviation `1.0`, adaptive
learning rate `0.001`, gamma `0.99`, lambda `0.95`, clip `0.2`, entropy
coefficient `0.001`, and desired KL `0.01`.

### Corrected learning curves

TensorBoard emitted the tags
`Episode_Reward/alignment_progress`,
`Episode_Reward/gated_axial_progress`, `Episode_Reward/success_bonus`,
`Episode_Termination/success`, `Episode_Termination/time_out`, `Loss/value`,
`Loss/surrogate`, `Loss/entropy`, `Loss/learning_rate`, `Policy/mean_std`,
`Perf/total_fps`, `Perf/collection_time`, `Perf/learning_time`,
`Train/mean_reward`, and `Train/mean_episode_length` (plus the two time
scalars).

| Iteration | Mean reward | Episode length | Alignment | Gated axial | Success | Timeout | Policy std |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | `-0.0001580493` | `14.7692` | `-0.0000519364` | `0.0000084797` | `0.0` | `0.0866` | `1.00875` |
| 100 | `0.17101355` | `183.57` | `0.0000888417` | `0.0007665357` | `0.4779` | `0.5221` | `0.62152` |
| 250 | `0.27003714` | `134.08` | `0.0000623611` | `0.0006740112` | `0.7747` | `0.2253` | `0.29093` |
| 500 | `0.26005206` | `136.17` | `0.0000540675` | `0.0005042322` | `0.7201` | `0.2799` | `0.22229` |
| 750 | `0.28013343` | `125.36` | `0.0000388868` | `0.0005001797` | `0.8477` | `0.1523` | `0.22211` |
| 999 | `0.28032142` | `123.59` | `0.0000586229` | `0.0007810174` | `0.8470` | `0.1530` | `0.22198` |

| Iteration | Value loss | Surrogate loss | Entropy | Learning rate |
| ---: | ---: | ---: | ---: | ---: |
| 0 | `0.0066021341` | `-0.0138441576` | `4.2716618` | `0.0015` |
| 100 | `0.0008983355` | `-0.0060357545` | `2.7382476` | `0.0019462` |
| 250 | `0.0011006193` | `-0.0071536638` | `0.0431101` | `0.0003844` |
| 500 | `0.0009648636` | `0.0010613324` | `-3.6342506` | `0.00001` |
| 750 | `0.0010220575` | `0.0088095106` | `-5.1051307` | `0.00001` |
| 999 | `0.0005025853` | `0.0148682566` | `-5.2198973` | `0.00001` |

The first logged positive gated-axial value was iteration `0`
(`8.47972e-06`), an initial random-rollout signal; a clearly larger positive
pulse appeared by iteration `33` (`3.67758e-04`).  The first non-zero success
termination was iteration `35` (`0.0130208`).  Alignment was non-zero from the
first step and remained active, unlike the invalid run.  The corrected curve
shows both axial descent and task termination emerging early, then settling
near 0.85 success termination in the later checkpoints.

### Corrected final checkpoint

`C:\dev\IsaacLab\logs\rsl_rl\ur10e_axial_credit\2026-08-28_20-14-38_exp021_axial_credit_trackerfix_seed42\model_999.pt`

SHA-256:

`17299F796D25E977116A9B4E7868CF92B93CE8CF9C6A78AB89CA3E3DEA380AB2`

## First-run final checkpoint (preserved evidence)

`C:\dev\IsaacLab\logs\rsl_rl\ur10e_axial_credit\2026-08-28_19-08-21_exp021_axial_credit_seed42\model_999.pt`

SHA-256:

`F098543C3136D07775297C4126F288CB646E966E0B315DCF62E92440EE5B20FB`

## First-run paired evaluation (invalidated control)

The exact Experiment 019 paired reset plan was reused:

- plan seed `43`
- plan SHA-256 `ece1662c6b5de3016c77b67c667b75f37551b3de80eaf137897645576abd2f2c`
- 64 environments × 4 episodes = 256
- deterministic inference
- IDs `env_00_ep_00` through `env_63_ep_03`

Command:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\021_ur10e_peg_in_hole_axial_credit\evaluate.py --mode paired --task Isaac-UR10e-PegInsert-AxialCredit-v1 --checkpoint C:\dev\IsaacLab\logs\rsl_rl\ur10e_axial_credit\2026-08-28_19-08-21_exp021_axial_credit_seed42\model_999.pt --num_envs 64 --episodes 256 --episodes-per-env 4 --paired-reset-seed 43 --seed 43 --output C:\Users\getch\AppData\Local\Temp\exp021-paired-46-seed43.json --headless --device cuda:0 --deterministic
```

Exit status was `0`; every environment consumed four planned episodes.  The
runtime spaces were policy `[64, 10]` and actions `[64, 3]`, with finite
observations.

| Policy | Success | Mean XY error | Median XY error | Mean max insertion | Median max insertion | Mean length | Mean reward |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen Experiment 018 | `219 / 256` (`85.5469%`) | `2.9876 mm` | `2.8789 mm` | `109.1742 mm` | `118.6697 mm` | `71.8164` | `0.2965152` |
| Experiment 020 precision | `0 / 256` (`0.0%`) | `0.9813 mm` | `0.9650 mm` | `0.0000 mm` | `0.0000 mm` | `239` | `0.000595925` |
| Experiment 021 axial credit | `0 / 256` (`0.0%`) | `367.8748 mm` | `368.3144 mm` | `0.0000 mm` | `0.0000 mm` | `239` | `-0.000482926` |

All 256 Experiment 021 episodes timed out.  No insertion depth or positive
contact diagnostic was recorded.  The full per-episode result is external at
`C:\Users\getch\AppData\Local\Temp\exp021-paired-46-seed43.json`.

## Corrected paired 256 evaluation

The repaired policy was evaluated on the same Experiment 019 reset plan:
64 environments × 4 planned episodes, seed `43`, plan SHA-256
`ece1662c6b5de3016c77b67c667b75f37551b3de80eaf137897645576abd2f2c`, and
deterministic inference.  Every environment consumed four planned episodes.

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\021_ur10e_peg_in_hole_axial_credit\evaluate.py --mode paired --task Isaac-UR10e-PegInsert-AxialCredit-v1 --checkpoint C:\dev\IsaacLab\logs\rsl_rl\ur10e_axial_credit\2026-08-28_20-14-38_exp021_axial_credit_trackerfix_seed42\model_999.pt --num_envs 64 --episodes 256 --episodes-per-env 4 --paired-reset-seed 43 --seed 43 --output C:\Users\getch\AppData\Local\Temp\exp021-trackerfix-paired-46-seed43.json --headless --device cuda:0 --deterministic
```

Exit status was `0`; runtime observations/actions were `[64, 10]` and
`[64, 3]`, and all observations were finite.  External output:
`C:\Users\getch\AppData\Local\Temp\exp021-trackerfix-paired-46-seed43.json`.

| Policy | Success | Mean XY error | Median XY error | Mean max insertion | Median max insertion | Mean length | Mean reward |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen Experiment 018 | `219 / 256` (`85.5469%`) | `2.9876 mm` | `2.8789 mm` | `109.1742 mm` | `118.6697 mm` | `71.8164` | `0.2965152` |
| Experiment 020 precision | `0 / 256` (`0.0%`) | `0.9813 mm` | `0.9650 mm` | `0.0000 mm` | `0.0000 mm` | `239` | `0.000595925` |
| Corrected Experiment 021 | `203 / 256` (`79.2969%`) | `2.9276 mm` | `2.6889 mm` | `56.4078 mm` | `62.8065 mm` | `122.5117` | `0.2710898` |

The corrected policy had 53 timeouts.  Paired-region counts were backward
`35 / 40`, center `54 / 67`, forward `40 / 49`, left `45 / 53`, and right
`29 / 47`.

## First-run comparison and known 34 failures (invalidated control)

`compare_three.py` validated the paired-plan SHA and all 256 stable IDs across
the frozen Experiment 018, Experiment 020, and Experiment 021 result files.
The comparison JSON is external at
`C:\Users\getch\AppData\Local\Temp\exp021-three-policy-comparison.json`.

For the pre-declared 34 IDs that were a 50 mm success and a 46 mm failure under
Experiment 018:

| Policy on the same 34 IDs | Success | Mean XY error | Mean max insertion | Recovered by 021 |
| --- | ---: | ---: | ---: | ---: |
| Experiment 018 at 46 mm | `0 / 34` | `4.2526 mm` | `49.3977 mm` | — |
| Experiment 020 at 46 mm | `0 / 34` | `0.8926 mm` | `0.0000 mm` | — |
| Experiment 021 at 46 mm | `0 / 34` | `378.4407 mm` | `0.0000 mm` | `0 / 34` |

The complete row-level records retain each episode ID, success flag, final XY,
insertion depth, and episode length for all three policies.  Experiment 021
did not retain the sub-3 mm alignment learned by Experiment 020 and did not
recover any of the known failures.

## Corrected known-34 recovery

The pre-declared subset is the same 34 stable IDs that were a 50 mm success and
a 46 mm failure for the frozen Experiment 018 policy.  The corrected three-way
comparison is:

| Policy on the same 34 IDs | Success | Mean XY error | Mean max insertion | Mean length |
| --- | ---: | ---: | ---: | ---: |
| Experiment 018 at 46 mm | `0 / 34` | `4.2526 mm` | `49.3977 mm` | `239` |
| Experiment 020 at 46 mm | `0 / 34` | `0.8926 mm` | `0.0000 mm` | `239` |
| Corrected Experiment 021 | `26 / 34` | `2.7705 mm` | `54.5675 mm` | `143.5588` |

The corrected policy recovered `26 / 34` known failures.  Among those 26
recovered episodes specifically, mean final XY error was `2.6527 mm`, mean
maximum insertion was `71.2407 mm`, and mean episode length was `114.1923`
steps.  The per-ID rows (including all three success flags, errors, depths, and
lengths) are in
`C:\Users\getch\AppData\Local\Temp\exp021-trackerfix-three-policy-comparison.json`.

## First-run hold-out seed 44 (invalidated control)

Command:

```powershell
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\021_ur10e_peg_in_hole_axial_credit\evaluate.py --mode holdout --task Isaac-UR10e-PegInsert-AxialCredit-v1 --checkpoint C:\dev\IsaacLab\logs\rsl_rl\ur10e_axial_credit\2026-08-28_19-08-21_exp021_axial_credit_seed42\model_999.pt --num_envs 64 --episodes 256 --episodes-per-env 4 --seed 44 --output C:\Users\getch\AppData\Local\Temp\exp021-holdout-seed44.json --headless --device cuda:0 --deterministic
```

Exit status was `0`; this was a different deterministic reset sequence.

| Metric | Experiment 021 hold-out |
| --- | ---: |
| Success | `0 / 256` (`0.0%`) |
| Mean / median final XY error | `366.9016 / 368.6850 mm` |
| Mean / median maximum insertion | `0.0000 / 0.0000 mm` |
| Mean episode length | `239` steps |
| Mean episodic reward | `-0.000479498` |
| Timeouts | `256` |

Region counts were backward `51`, center `67`, forward `34`, left `58`, and
right `46`; every region had zero successes.  The external JSON is
`C:\Users\getch\AppData\Local\Temp\exp021-holdout-seed44.json`.

## Corrected hold-out seed 44

The repaired checkpoint was evaluated on a different deterministic reset
sequence with 256 completed episodes:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\021_ur10e_peg_in_hole_axial_credit\evaluate.py --mode holdout --task Isaac-UR10e-PegInsert-AxialCredit-v1 --checkpoint C:\dev\IsaacLab\logs\rsl_rl\ur10e_axial_credit\2026-08-28_20-14-38_exp021_axial_credit_trackerfix_seed42\model_999.pt --num_envs 64 --episodes 256 --seed 44 --output C:\Users\getch\AppData\Local\Temp\exp021-trackerfix-holdout-seed44.json --headless --device cuda:0 --deterministic
```

Exit status was `0`; the runtime observations/actions were `[64, 10]` and
`[64, 3]`, and all observations were finite.  External output:
`C:\Users\getch\AppData\Local\Temp\exp021-trackerfix-holdout-seed44.json`.

| Metric | Corrected Experiment 021 |
| --- | ---: |
| Success | `210 / 256` (`82.0313%`) |
| Mean / median final XY error | `2.7694 / 2.6443 mm` |
| Mean / median maximum insertion | `60.7225 / 63.3355 mm` |
| Mean episode length | `122.8398` steps |
| Mean episodic reward | `0.2803367` |
| Timeouts | `46` |

Hold-out region counts were backward `36 / 45`, center `55 / 66`, forward
`31 / 37`, left `54 / 61`, and right `34 / 47`.

## First-run classification (invalidated)

`CONTROLLED_COMPARISON_INVALIDATED`

`REWARD_TRACKER_COUPLING_FOUND`

The first run remains preserved evidence: its TensorBoard curves, final
checkpoint hash, `0 / 256` paired result, approximately `367 mm` final XY
error, and zero-success hold-out result are recorded above.  Because
`_axial_tracker_valid` prevented the unchanged alignment tracker from ever
becoming valid, that run cannot determine whether signed axial credit itself
worked or failed.  It is retained as the implementation-confound control.

## Corrected classification

`STATE_ONLY_AXIAL_CREDIT_ESTABLISHED`

The repaired policy materially improved over Experiment 020 (`0 / 256`) on
the exact paired plan (`203 / 256`, `79.2969%`) and also succeeded on the
independent seed-44 hold-out (`210 / 256`, `82.0313%`).  It reached substantial
insertion depth (paired mean `56.4078 mm`, hold-out mean `60.7225 mm`) while
retaining 3 mm-scale final XY error (paired mean `2.9276 mm`, hold-out mean
`2.7694 mm`).  This establishes the state-only axial-credit experiment for
the observed 3 mm failure regime; force/contact observations were not needed
for this result.  It does not generalize the conclusion to the 2 mm task.

## Paired GUI replay (attempted)

The selected stable known-34 episode was `env_00_ep_03` (Experiment 020
aligned and timed out; corrected Experiment 021 succeeded).  Its exact fixed
inputs were hole offset `[3.758712, 15.319010] mm` and peg initial offset
`[-1.977956, -9.714357] mm`.

The external replay script used the existing native Learning UI, the same
single environment, and both checkpoints:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\Users\getch\AppData\Local\Temp\exp021_gui_paired_replay.py --checkpoint-020 C:\dev\IsaacLab\logs\rsl_rl\ur10e_state_precision\2026-08-28_17-43-39_exp020_state_precision_seed42\model_999.pt --checkpoint-021 C:\dev\IsaacLab\logs\rsl_rl\ur10e_axial_credit\2026-08-28_20-14-38_exp021_axial_credit_trackerfix_seed42\model_999.pt --hole-x-mm 3.758712 --hole-y-mm 15.31901 --peg-x-mm -1.977956 --peg-y-mm -9.714357 --steps 240 --seed 43 --output C:\Users\getch\AppData\Local\Temp\exp021-trackerfix-gui-paired-env00ep03.json --viz kit --device cuda:0
```

Two attempts returned the batch wrapper's code `0` but did not create the
JSON.  Kit logged
`Simulation view object is invalidated and cannot be used again to call
GpuSimulationView::updateArticulationsKinematic` and shut down before the
policy loop.  Therefore this paired visual replay is **not** claimed as
completed.  The separate corrected `gui_probe.py` run above did complete and
verified that the existing UI labels update; the quantitative paired and
hold-out results remain the authoritative policy evidence.

## Runtime warnings and resource evidence

The runs repeatedly emitted the existing Isaac Sim/PhysX warnings: missing
`_isaac_sim\setup_conda_env.bat`, a Linux-only `libcarb.so` Fabric notice with
a Windows CP949 logging error, missing `isaaclab_visualizers` extension
configuration, MaterialX/Fabric/warp notices, TGS noisy-velocity messages, and
disjointed `ee_joint` transform warnings.  The paired GUI policy replay also
logged a `GpuSimulationView::updateArticulationsKinematic` invalidation and
produced no replay output; that boundary is reported separately above.  No OOM
or task exception appeared in the finite probes, smoke, or corrected
full-training log.  A post-run `nvidia-smi` sample after corrected evaluation
reported RTX 4070 Ti memory `1506 MiB / 12282 MiB`, driver `591.86`; no
continuous peak monitor was running for the corrected training.  The earlier
invalid run's sampled range (`3.89` to `6.099 GB`) remains historical evidence,
not a corrected-run peak.

Generated checkpoints, TensorBoard event files, videos, caches, and JSON
results remain external and untracked.

## Repository files

Only this directory is part of Experiment 021:

- `registration.py` — task IDs, config, and the three-term reward contract
- `runtime.py` — signed gated axial reward and native UI additions
- `prekit_check.py` — finite configuration gate
- `semantic_probe.py` — reward-credit semantic trajectory
- `gui_probe.py` — native Learning UI runtime probe
- `random_baseline.py` — 128-episode random baseline
- `evaluate.py` — Experiment 020 evaluator invoked for the 021 task
- `compare_three.py` — fixed-plan three-policy and known-34 comparison
- `README.md` — this evidence record

Experiments 018–020 and `src/robotics_rnd` are unchanged.  The generated
evidence paths above are intentionally outside the repository.
