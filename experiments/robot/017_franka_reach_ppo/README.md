# Experiment 017 — Franka Reach PPO Baseline

## Question

Can the official Isaac Lab Franka Reach environment execute a reproducible
PPO training pipeline on this workstation, and what evidence is required
before claiming the reaching task was learned?

## Hypothesis

The official environment should support finite PhysX rollouts and RSL-RL PPO
updates on the RTX 4070 Ti workstation, but a five-iteration smoke test alone
will not demonstrate task learning.

## External Environment

- Isaac Lab source commit: `418ca31b47a8eb27db8aefcfc134e4c4f1d2b6f3`
- Git describe: `v3.0.0-beta2.patch1-5-g418ca31b4`
- Isaac Sim: `6.0.1-rc.7+release.42383.32955d8d.gl`
- OS: Windows 11
- GPU: NVIDIA GeForce RTX 4070 Ti, 12 GiB class
- Torch: `2.10.0+cu128`
- RSL-RL: `5.0.1`
- Physics: PhysX

Commit `418ca31` was selected because the previous official patch1 commit
referenced a removed Franka asset path. The later official release-branch fix
moved the path under `FrankaEmika/Legacy`; this is an upstream revision, not a
local patch.

## Task Reconstruction

Runtime-confirmed policy observation dimension: `32`.

- `joint_pos`: 9
- `joint_vel`: 9
- `pose_command`: 7
- `previous_action`: 7

Action dimension: `7`.

Resolved joints are `panda_joint1` through `panda_joint7`. The physics
timestep is `1/60 s`, the environment/control timestep is `1/30 s`, and the
episode length is `12 s`.

## Upstream Validation

Exact official finite-test command:

```text
C:\dev\IsaacLab\isaaclab.bat -p -m pytest source\isaaclab_tasks\test\test_environments.py -k "Isaac-Reach-Franka-v0" --capture=no -q
```

Result: process exit `0`; `2 passed`, `180 deselected`; 100 random-action
steps per selected configuration; `num_envs=1 PASS`; `num_envs=2 PASS`.

Pytest capture had a Windows compatibility issue: fd capture produced an
invalid stderr handle, while sys capture lacked `fileno()`. `capture=no`
preserved the real file descriptors and allowed the unchanged upstream test
to run. No Isaac Lab source modification was made.

## PPO Pipeline Smoke

- `num_envs`: 64
- `num_steps_per_env`: 24
- `iterations`: 5
- `seed`: 42
- Total transitions: `7,680`
- Actor: `[64, 64]`, ELU
- Critic: `[64, 64]`, ELU
- Initial action standard deviation: `1.0`
- Gamma: `0.99`
- Lambda: `0.95`
- PPO clip: `0.2`
- Entropy coefficient: `0.001`
- Desired KL: `0.01`

Exact training command:

```text
C:\dev\IsaacLab\isaaclab.bat train --rl_library rsl_rl --task Isaac-Reach-Franka-v0 --num_envs 64 --max_iterations 5 --seed 42 --deterministic --headless --logger tensorboard --run_name exp017_smoke_seed42 --device cuda:0 physics=physx
```

The process exited `0`; wrapper wall time was `22.264 s`, and RSL-RL reported
`7.98 seconds` of training time.

## Observed Metrics

The following are first-to-final TensorBoard scalar values from the five
iterations. They are not evidence of convergence.

| Metric | First → final |
| --- | ---: |
| `Train/mean_reward` | `-0.149024 → -0.456565` |
| `Train/mean_episode_length` | `14.0 → 65.285713` |
| `Metrics/success_rate` | `0.0 → 0.541667` |
| `Metrics/ee_pose/position_error` | `0.457928 → 0.201002` |
| `Metrics/ee_pose/orientation_error` | `1.953481 → 1.891637` |
| `Loss/value` | `0.004681 → 0.002380` |
| `Loss/surrogate` | `-0.022376 → -0.012885` |
| `Policy/mean_std` | `0.998150 → 0.998446` |
| `Loss/learning_rate` | `0.000010 → 0.000010` |

Position-error and success metrics improved during the smoke. Episodic mean
reward became more negative while mean episode length increased. Five
iterations are insufficient to infer learning or convergence; `success_rate`
is not equivalent to per-target task completion. Zero-action/random-policy
and trained-policy evaluation has not yet been run.

## External Generated Evidence

Generated artifacts remain outside this repository at:

```text
C:\dev\IsaacLab\logs\rsl_rl\franka_reach\2026-08-27_00-59-27_exp017_smoke_seed42
```

Checkpoint SHA-256 hashes:

- `model_0.pt`: `CE3AE2BFFABBCBC887D377D51FE555BCDE09CA096AF96D5F6F5549FB7907D712`
- `model_4.pt`: `DCB6CBD5DFE5C4F1BDE16A37F624C6CB4575BCB4F18B2AE91F779B05B07C1277`

Checkpoints, TensorBoard event files, logs, and simulator outputs remain
external and untracked.

## Result

Classification: `PIPELINE_VERIFIED` / `LEARNING_NOT_ESTABLISHED`.

Evidence:

- official finite environment test passed;
- 64-environment rollout collection passed;
- PPO optimization passed;
- TensorBoard logging passed;
- checkpoint creation passed.

Not established:

- convergence;
- reliable reaching performance;
- trained-vs-baseline superiority;
- cross-seed reproducibility;
- robustness.

## Decision

`continue`

Next experiment phase: run the unchanged full official PPO baseline and
evaluate it quantitatively before changing reward, observation, action, or
hyperparameters.
