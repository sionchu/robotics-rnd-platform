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

## Paired Reset Follow-Up

The initial four runs above used the same seed and reset distributions, but
vectorized environments reset in a different completion order as the aperture
tightened.  This follow-up removes that ordering confounder without changing
the policy or task: one explicit reset plan was replayed at the `50 mm / 5 mm`
and `46 mm / 3 mm` levels.

The plan is deterministic and external to the simulator RNG.  It uses
`Python random.Random(seed)` (MT19937), iterates env-major, performs four
uniform draws per episode, and rounds values to `1e-6 mm`:

- plan/evaluation seed: `43`;
- dimensions: `64` environments × `4` episodes = `256` paired episodes;
- hole offsets: `X ±40 mm`, `Y ±30 mm`;
- initial peg offsets: `X ±15 mm`, `Y ±15 mm`;
- plan SHA-256: `ece1662c6b5de3016c77b67c667b75f37551b3de80eaf137897645576abd2f2c`.

Each JSON record has a stable ID (`env_00_ep_00` through
`env_63_ep_03`) and contains the planned offsets, success/timeout flags,
final XY error, final and maximum insertion depth, episode length, episodic
reward, maximum wrist contact diagnostic, region, and misaligned-insertion
flag.  The RSL-RL wrapper's internal warm-up reset used the original reset
function; the explicit evaluator began at plan episode `0` for every
environment.  Both runs consumed exactly four planned entries per
environment.

Exact commands (generated summaries and logs remain outside Git):

```powershell
$script = 'C:\dev\robotics-rnd-platform\experiments\robot\019_ur10e_peg_in_hole_precision\precision_probe.py'
$checkpoint = 'C:\dev\IsaacLab\logs\rsl_rl\ur10e_peg_insert_learning\2026-08-28_02-40-31_exp018_v1_baseline_seed42\model_999.pt'
$env:PYTHONPATH = 'C:\dev\robotics-rnd-platform'
Set-Location C:\dev\IsaacLab
.\isaaclab.bat -p $script --task Isaac-UR10e-PegInsert-Learning-v1 --checkpoint $checkpoint --hole_mm 50 --num_envs 64 --episodes 256 --seed 43 --paired-reset-seed 43 --episodes-per-env 4 --output C:\Users\getch\AppData\Local\Temp\exp019-paired-50-seed43-final.json --headless --device cuda:0
.\isaaclab.bat -p $script --task Isaac-UR10e-PegInsert-Learning-v1 --checkpoint $checkpoint --hole_mm 46 --num_envs 64 --episodes 256 --seed 43 --paired-reset-seed 43 --episodes-per-env 4 --output C:\Users\getch\AppData\Local\Temp\exp019-paired-46-seed43-final.json --headless --device cuda:0
```

### Paired Performance

| Hole | Side clearance | Success | Mean final XY | Median final XY | Mean max insertion | Median max insertion | Mean episode length | Mean reward |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 mm | 5 mm | 252/256 (98.4375%) | 4.4307 mm | 4.5276 mm | 79.4248 mm | 63.9306 mm | 25.7188 | 0.3364138 |
| 46 mm | 3 mm | 219/256 (85.5469%) | 2.9876 mm | 2.8789 mm | 109.1742 mm | 118.6697 mm | 71.8164 | 0.2965152 |

The `50 mm` run took `355` vector steps (`14.4560 s` evaluator elapsed;
`35.4130 s` wall in the Isaac Lab wrapper).  The `46 mm` run took `574`
vector steps (`22.0998 s` evaluator elapsed; `37.3085 s` wall in the wrapper).
All `256` planned records and reset events were present in each output.

| Hole | Mean max wrist contact | Median max wrist contact | Maximum wrist contact |
| ---: | ---: | ---: | ---: |
| 50 mm | 29.2193 N | 13.9756 N | 107.6450 N |
| 46 mm | 68.5698 N | 73.5678 N | 118.3629 N |

### Paired Outcome Cells

Joining the two outputs by stable episode ID gives the following exact
comparison:

| 50 mm / 5 mm | 46 mm / 3 mm | Episodes |
| --- | --- | ---: |
| success | success | 218 |
| success | failure/timeout | 34 |
| failure/timeout | success | 1 |
| failure/timeout | failure/timeout | 3 |

Thus `34` of the `37` failures at `46 mm / 3 mm` are newly introduced by the
tighter aperture under identical reset inputs.  Three episodes fail at both
levels, and one episode is successful only at the tighter level; those raw
cells are retained rather than averaged away.

### Failure Localization

For the `34` success-at-50 / failure-at-46 episodes:

| Quantity | Mean | Median | Minimum | Maximum |
| --- | ---: | ---: | ---: | ---: |
| Hole X offset | 7.9729 mm | 14.5056 mm | -39.7906 mm | 38.8133 mm |
| Hole Y offset | -3.1150 mm | -7.5313 mm | -28.7646 mm | 28.5674 mm |
| Initial peg XY magnitude | 13.5063 mm | 13.4450 mm | 4.8155 mm | 20.4514 mm |
| Initial peg X offset | -5.8263 mm | -7.0820 mm | -14.6576 mm | 14.7275 mm |
| Initial peg Y offset | -5.6868 mm | -9.8227 mm | -14.6737 mm | 12.2279 mm |
| 46 mm final XY error | 4.2526 mm | 4.2227 mm | 3.1999 mm | 5.5891 mm |
| 46 mm maximum insertion | 49.3977 mm | 52.6882 mm | 0.0000 mm | 118.8551 mm |
| 46 mm episode length | 239.0000 | 239.0000 | 239.0000 | 239.0000 |
| 46 mm maximum wrist contact | 47.8885 N | 45.1945 N | 22.8926 N | 89.7992 N |

All `37` failures at `46 mm / 3 mm` timed out and had final XY error above
the declared `3 mm` tolerance (minimum `3.1549 mm`).  Across all 37 failures,
mean maximum insertion was `55.0270 mm` and mean maximum wrist contact was
`50.0454 N`; successful episodes averaged `118.3223 mm` maximum insertion and
`71.6995 N` contact.  The lower contact statistic in the failure subset does
not support contact force as the primary explanation for the `3 mm` boundary.
The wrist sensor is retained as a diagnostic, not a calibrated peg-wall force
measurement.

The initial peg-offset sign quadrants for those 37 failures were `x-/y-: 21`,
`x-/y+: 8`, `x+/y-: 4`, and `x+/y+: 4`.  This descriptive skew, together with
the larger failure-subset offset magnitude, is not treated as a causal result.

Region counts for the same paired IDs are:

| Region | Episodes | 50 mm successes | 46 mm successes | 50-success → 46-failure |
| --- | ---: | ---: | ---: | ---: |
| center | 67 | 67 | 57 | 10 |
| left | 53 | 53 | 50 | 3 |
| right | 47 | 43 | 35 | 9 |
| forward | 49 | 49 | 44 | 5 |
| backward | 40 | 40 | 33 | 7 |

Right-side resets have the highest `46 mm` failure count (`12/47`), followed
by center (`10/67`) and backward (`7/40`); failures occur in every region and
are not isolated to one location.

## Classification

The original four-level probe remains `PRECISION_BOUNDARY_MEASURED`.  The
paired follow-up adds:

`PAIRED_PRECISION_FAILURE_LOCALIZED`

The evidence supports a predominantly state-based precision failure at the
`46 mm / 3 mm` boundary under identical reset inputs.  It does not establish
force awareness or a causal contact model; the earlier `44 mm / 2 mm` shallow,
high-contact failures remain a separate contact-aware insertion question.

## Next Best Action

Keep Experiment 018 and the frozen checkpoint unchanged.  If learning is
authorized next, start a separate Experiment 020 that learns state-based
precision at `46 mm / 3 mm` with the same explicit reset-plan evaluation, then
investigate contact-aware insertion separately.  Do not tune the frozen policy
inside this evaluation commit.
