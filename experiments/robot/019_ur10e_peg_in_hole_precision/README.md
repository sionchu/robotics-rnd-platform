# Experiment 019 — Peg-in-Hole Precision Boundary Probe

## Question

At what square-aperture clearance does the frozen Experiment 018 UR10e
peg-in-hole policy begin to fail, and is the boundary caused primarily by
state-based XY precision or by contact blocking descent?

No policy weights were changed and no PPO training was run.

## Experiment Boundary

Experiment 019 is a new evaluation-only boundary.  It imports the authoritative
Experiment 018 task, robot asset, observation/action contract, reward weights,
reset ranges, and RSL-RL policy, then changes only the parsed primitive fixture
geometry and the geometry-consistent success predicate in process memory.

Experiment 018 source files remain untouched.  The frozen checkpoint is:

`C:\dev\IsaacLab\logs\rsl_rl\ur10e_peg_insert_learning\2026-08-28_02-40-31_exp018_v1_baseline_seed42\model_999.pt`

SHA-256:

`D5D9AED8CA05D6BF5A9E64357BE146DD8E10782646ADEDC3E255A962CCF7CFAF`

## Geometry

The peg remains an axis-aligned `40 mm × 40 mm` square.  Only the square hole
side and the four primitive wall positions/sizes change:

| Hole side | Total side gap | Side clearance per wall |
| ---: | ---: | ---: |
| 50 mm | 10 mm | 5 mm |
| 48 mm | 8 mm | 4 mm |
| 46 mm | 6 mm | 3 mm |
| 44 mm | 4 mm | 2 mm |

The lateral success tolerance is declared before evaluation as:

`success_xy_tolerance = min(5 mm, (hole_side − peg_side) / 2)`

Therefore the success tolerances are exactly `5, 4, 3, 2 mm` for the four
levels.  The policy reports Euclidean XY error; `L2 ≤ side clearance` implies
each individual axis error is within the clearance, so this predicate cannot
declare an axis-aligned square peg to fit when its aperture is geometrically
too small.  The insertion-depth criterion remains `60 mm`.

The action scale, DLS lambda, orientation, observation shape, reward weights,
alignment gate, reset ranges, plate, UR10e, PhysX, and checkpoint are unchanged.
The success predicate and its existing success bonus use the declared
geometry-consistent tolerance; no reward weight or additional force term was
added.

## Evaluation Protocol

Each level used the same official Experiment 018 task entry point, checkpoint,
deterministic inference, `64` environments, `256` completed episodes, seed
`43`, headless Kit, CUDA, and PhysX.  The repository script is
`precision_probe.py`; generated JSON and logs remain external.

```powershell
$script = 'C:\dev\robotics-rnd-platform\experiments\robot\019_ur10e_peg_in_hole_precision\precision_probe.py'
$checkpoint = 'C:\dev\IsaacLab\logs\rsl_rl\ur10e_peg_insert_learning\2026-08-28_02-40-31_exp018_v1_baseline_seed42\model_999.pt'
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p $script `
  --task Isaac-UR10e-PegInsert-Learning-v1 `
  --checkpoint $checkpoint `
  --hole_mm <50|48|46|44> `
  --num_envs 64 `
  --episodes 256 `
  --seed 43 `
  --output C:\Users\getch\AppData\Local\Temp\exp019-precision-<hole>-seed43.json `
  --headless `
  --device cuda:0
```

The initial 64-environment reset batch was identical across all four runs
(digest `d13135303b44cd2db7414203062a3b339ac9846889109e04d2a2b7f9867251e7`).
Later vectorized reset ordering diverged because tighter holes changed episode
completion times; all runs still used seed `43` and the same frozen reset
distribution.  This ordering limitation is retained rather than hidden.

## Precision Results

All four executions exited `0`.

| Hole | Side clearance | Tolerance | Success | Mean XY error | Median XY error | Mean max insertion | Median max insertion | Mean episode length | Mean reward |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 mm | 5 mm | 5 mm | 256/256 (100.0000%) | 4.3390 mm | 4.3764 mm | 75.4935 mm | 63.3184 mm | 20.8867 | 0.3412653 |
| 48 mm | 4 mm | 4 mm | 256/256 (100.0000%) | 3.7028 mm | 3.7504 mm | 117.3941 mm | 117.8940 mm | 40.2227 | 0.3455049 |
| 46 mm | 3 mm | 3 mm | 236/256 (92.1875%) | 2.8565 mm | 2.8519 mm | 112.8797 mm | 118.6137 mm | 58.9844 | 0.3190598 |
| 44 mm | 2 mm | 2 mm | 183/256 (71.4844%) | 2.5736 mm | 1.8947 mm | 89.8720 mm | 119.2729 mm | 100.4922 | 0.2477318 |

External summaries:

- `C:\Users\getch\AppData\Local\Temp\exp019-precision-50-seed43.json`
- `C:\Users\getch\AppData\Local\Temp\exp019-precision-48-seed43.json`
- `C:\Users\getch\AppData\Local\Temp\exp019-precision-46-seed43.json`
- `C:\Users\getch\AppData\Local\Temp\exp019-precision-44-seed43.json`

## Failure Boundary

The first non-zero failure rate occurs at `46 mm / 3 mm` side clearance:

- `50 mm / 5 mm`: no failures;
- `48 mm / 4 mm`: no failures, but contact rises sharply;
- `46 mm / 3 mm`: `20` timeouts, `92.1875%` success;
- `44 mm / 2 mm`: `73` timeouts, `71.4844%` success.

The boundary is therefore measured between `4 mm` and `3 mm` side clearance,
with a substantially degraded regime at `2 mm`.

## Region Results

| Hole | Center | Left | Right | Forward | Backward |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 50 mm | 50/50 | 60/60 | 40/40 | 56/56 | 50/50 |
| 48 mm | 62/62 | 65/65 | 34/34 | 52/52 | 43/43 |
| 46 mm | 50/58 | 57/58 | 37/42 | 44/47 | 48/51 |
| 44 mm | 34/50 | 37/50 | 30/45 | 42/55 | 40/56 |

Entries are `successes / episodes`.

## Contact Evidence

The existing `wrist_contact` sensor was retained as a diagnostic; no force
observation or force reward was introduced.

| Hole | Mean max contact | Median max contact | Maximum contact | Contact-positive episodes |
| ---: | ---: | ---: | ---: | ---: |
| 50 mm | 26.4316 N | 13.4793 N | 89.8549 N | 256/256 |
| 48 mm | 74.9269 N | 78.1926 N | 114.1462 N | 256/256 |
| 46 mm | 71.8423 N | 75.3212 N | 201.7634 N | 256/256 |
| 44 mm | 73.2399 N | 74.4464 N | 305.6304 N | 256/256 |

Failure-subset evidence:

| Hole | Failed/timeouts | Failed mean final XY | Failed mean max insertion | Failed mean max contact | Inserted before 10 mm alignment gate |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 46 mm | 20/20 | 3.9409 mm | 64.5796 mm | 73.0103 N | 1/20 |
| 44 mm | 73/73 | 4.5480 mm | 16.3913 mm | 70.2363 N | 0/73 |

At `46 mm`, failed episodes usually reached around the 60 mm depth criterion
but missed the 3 mm lateral tolerance; only one failure showed measurable
insertion before the 10 mm alignment gate.  At `44 mm`, failed episodes usually
stopped near the top (`16.3913 mm` mean maximum depth) while contact remained
high, indicating that wall contact blocks descent in many trials.  The sensor
is on `wrist_3_link`, so these values are contact diagnostics rather than a
calibrated peg-wall force measurement.

## GUI Comparison

After the quantitative runs, both the 5 mm and first degraded 3 mm clearance
were replayed in the existing Learning Lab Kit UI with one environment, seed
`43`, the same checkpoint, and mode `TRAINED PPO`.

| Level | Steps | Video | Inspected desktop capture |
| --- | ---: | --- | --- |
| Hole 50 mm / clearance 5 mm | 240 | `C:\Users\getch\AppData\Local\Temp\exp019-precision-gui-50-seed43\rl-video-step-0.mp4` | `C:\Users\getch\AppData\Local\Temp\exp019-precision-gui-50-seed43\desktop-50-2.png` |
| Hole 46 mm / clearance 3 mm | 240 | `C:\Users\getch\AppData\Local\Temp\exp019-precision-gui-46-seed43\rl-video-step-0.mp4` | `C:\Users\getch\AppData\Local\Temp\exp019-precision-gui-46-seed43\desktop-46-1.png` |

The added external label shows `Hole`, `Clearance`, `Frozen PPO`, seed `43`,
and `TRAINED PPO`; both captures show the same UR10e/plate/camera style and
randomized hole UI.  The videos are `1280 × 720`, `30 fps`, `240` frames,
`8 s`.  Playback is visual evidence only, not an additional success estimate.

## Interpretation

1. The frozen policy first fails at `3 mm` side clearance (`46 mm` hole), with
   a stronger failure regime at `2 mm`.
2. At `46 mm`, the dominant measured failure signature is insufficient final
   XY precision at the tighter tolerance: failed episodes averaged `3.9409 mm`
   final XY error while reaching `64.5796 mm` maximum depth.  At `44 mm`, high
   contact and shallow `16.3913 mm` maximum depth indicate that contact blocks
   descent for many failures.
3. The policy appears to sit near the original 5 mm physical/tolerance
   boundary: it remains fully successful at 4 mm, then loses 7.8125 percentage
   points at 3 mm and 28.5156 points at 2 mm.  This is evidence about this
   frozen policy and simulation geometry, not a universal clearance claim.
4. The immediate next learning problem is better state-based precision at the
   3 mm boundary; once that is addressed, the 2 mm results show a separate
   contact/force-aware insertion problem.  No force-aware controller was added
   here.

## Repository Diff

New Experiment 019 files:

- `README.md` — frozen geometry rule, commands, measured results, diagnostics,
  GUI evidence, and limitations;
- `precision_probe.py` — one-off evaluator that imports Experiment 018 and
  applies process-local aperture/tolerance overrides;
- `precision_gui.py` — one-off GUI comparison runner with a static geometry
  label.

Experiment 018 implementation and README were not modified.  No checkpoints,
videos, logs, caches, root dependencies, reusable-platform modules, or force
features were added to Git.

## Classification

`PRECISION_BOUNDARY_MEASURED`

This does not claim robustness to all clearances, sim-to-real readiness, or
force awareness.

## Next Best Action

Run one paired-reset follow-up at the measured `46 mm / 3 mm` boundary using a
pre-generated seed-43 reset plan, then decide whether state-based precision
learning or contact-aware insertion should be isolated first.  Do not tune the
policy in this boundary-probe commit.
