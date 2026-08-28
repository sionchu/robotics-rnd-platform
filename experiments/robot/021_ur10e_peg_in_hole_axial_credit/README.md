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
tracker is reset per environment and does not add a fourth reward term.

## Pre-training gates

`prekit_check.py` passed with the two task IDs, 46/3 geometry, 10-value
observation contract, 3-action DLS controller, exactly three reward terms, and
the frozen PPO values.  The finite GUI probe also passed with one environment.

### Reward-credit semantic probe

Command:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\021_ur10e_peg_in_hole_axial_credit\semantic_probe.py --task Isaac-UR10e-PegInsert-AxialCredit-v1 --steps 220 --seed 42 --output C:\Users\getch\AppData\Local\Temp\exp021-semantic-probe.json --headless --device cuda:0
```

Exit status was `0`.  The probe ran 220 steps and demonstrated both required
conditions:

- while above the hole top, `insertion_depth == 0` occurred;
- while still above the top and inside the `10 mm` XY gate, axial progress was
  positive.

The first positive record was step `23`: XY error `9.9516 mm`, Z error
`25.1280 mm`, axial remaining `85.1280 mm`, insertion depth `0 mm`, and axial
reward `+3.04878e-05`.  A negative above-gate value was also observed for an
upward motion, preserving the signed behavior.  This is the core semantic gate
for 021 and is recorded in the external JSON above.

### Native Learning UI probe

Command:

```powershell
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p C:\dev\robotics-rnd-platform\experiments\robot\021_ur10e_peg_in_hole_axial_credit\gui_probe.py --task Isaac-UR10e-PegInsert-AxialCredit-Play-v1 --steps 180 --seed 42 --output C:\Users\getch\AppData\Local\Temp\exp021-gui-probe.json --viz kit --device cuda:0
```

Exit status was `0`.  The native Learning UI displayed the flow
`ALIGN ↓ AXIAL APPROACH ↓ INSERT ↓ SUCCESS`, `Axial Remaining: xx.x mm`, and
`Axial Progress Reward: +x.xxxx`.  The scripted probe crossed the hole top and
reported insertion depth; this is a visualization/runtime check, not a claim
about the trained policy.

## Random baseline

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

## 1,000-iteration training

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

## Learning curves

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

## Final checkpoint

`C:\dev\IsaacLab\logs\rsl_rl\ur10e_axial_credit\2026-08-28_19-08-21_exp021_axial_credit_seed42\model_999.pt`

SHA-256:

`F098543C3136D07775297C4126F288CB646E966E0B315DCF62E92440EE5B20FB`

## Paired 256 evaluation

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

## Three-policy comparison and known 34 failures

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

## Hold-out seed 44

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

## Classification

`STATE_ONLY_AXIAL_CREDIT_NOT_ESTABLISHED`

The semantic probe proves that the new reward supplies the intended positive
above-top axial credit, but the freshly trained policy produced zero paired
successes, zero hold-out successes, zero insertion depth, and 256 timeouts in
both evaluations.  It also lost the precise XY behavior seen in Experiment
020.  The single next bottleneck is policy/exploration collapse under the
signed, gated axial reward signal; this result does not establish that force
or contact observations are required and says nothing about the 2 mm task.

The paired GUI replay and the nine-environment parallel visual were not run
because the pre-declared learning condition was not met.  No 2 mm training or
evaluation was run.

## Runtime warnings and resource evidence

The runs repeatedly emitted the existing Isaac Sim/PhysX warnings: missing
`_isaac_sim\setup_conda_env.bat`, a Linux-only `libcarb.so` Fabric notice with
a Windows CP949 logging error, missing `isaaclab_visualizers` extension
configuration, MaterialX/Fabric/warp notices, TGS noisy-velocity messages, and
disjointed `ee_joint` transform warnings.  No OOM or task exception appeared
in the finite probes, smoke, or full-training log.  Sampled `nvidia-smi`
observations during full training showed RTX 4070 Ti memory from about `3.89`
to `6.099 GB` of `12.282 GB`; this was sampled rather than a continuous peak
monitor.

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
