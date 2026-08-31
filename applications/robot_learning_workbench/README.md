# Robot Learning Workbench

Robot Learning Workbench is a dependency-light Windows desktop application for
understanding and operating this repository's evidence-first robot-learning
workflow. It is a thin orchestration and teaching layer over canonical
experiments and an existing external Isaac Lab installation. It is not an RL
framework, task editor, or Isaac Sim replacement.

## Architecture boundary

```text
tkinter desktop process (standard library only)
        |
        | exact cwd/env/argv + subprocess + explicit JSON output
        v
isaac_probe.py through isaaclab.bat
        |
        +-- Isaac Lab / Isaac Sim task configuration
        +-- native Isaac GUI
        +-- existing TensorBoard event reader
```

The desktop process never imports Isaac Lab, Omni, USD, Torch, RSL-RL, or
TensorBoard. Machine paths and local experiment notes are stored under:

```text
%LOCALAPPDATA%\robotics-rnd-platform\robot-learning-workbench\settings.json
```

No workstation path is written to repository files.

## Launch

From the repository root using its normal Python environment:

```powershell
.\.venv\Scripts\python.exe -m applications.robot_learning_workbench
```

Use **File > Open Workspace** and **File > Configure Isaac Lab** if the detected
locations are not correct. The application never installs or repairs either
environment.

## Screen layout

```text
+-----------------------------------------------------------------------+
| File | Workspace | Asset | Task | Training | Evaluation | View       |
+-----------------------------------------------------------------------+
| Toolbar: Open | Refresh | Probe | Launch GUI | Stop | Copy Command   |
+------------------+-----------------------------+----------------------+
| Project Explorer | Overview / Asset / Task-MDP | Property / Explain   |
|                  | Training / Evaluation       | source and values    |
+------------------+-----------------------------+----------------------+
| Timestamped command and process console                               |
+-----------------------------------------------------------------------+
| Repo | Isaac Lab | Task | tracked process | GPU                       |
+-----------------------------------------------------------------------+
```

## Workflow

1. Inspect workspace and external runtime readiness.
2. Select an AST-discovered experiment and task.
3. Run the external task probe to load canonical scene and MDP metadata.
4. Inspect configured assets by scene role, or catalog an external
   USD/URDF/MJCF path without copying it.
5. Read Goal, Success, Observation, Action, Reward, Termination, Reset, then PPO.
   Instantiated tasks attach runtime-probed scalar dimensions to each canonical
   observation term while retaining the verified total observation dimension.
6. Preview and launch the native Isaac task GUI; record visual review manually.
7. Preview the exact experiment-provided semantic, random, evaluation, PPO
   smoke, or full-config command before running; unavailable stages show N/A.
8. Read existing TensorBoard scalar files through the external helper.
9. Optionally tail a single-environment JSONL file to inspect state, action,
   physical action scale, reward gates, success, and episode values.
10. Open evaluation JSON files and compare metrics, stable episode IDs, regions,
   and experiment-provided failure taxonomy.

Guided Mode adds Korean practical explanations to the same probed data shown in
Engineering Mode. Engineering Mode exposes task IDs, source modules, config
classes, constants, paths, raw metric names, and exact commands.

Isaac commands run with the Isaac Lab checkout as their working directory and
an explicit repository `PYTHONPATH`, so generated training artifacts stay under
the external Isaac Lab run tree rather than the repository.

## Deliberate exclusions

V0 does not edit experiment source, rewards, PPO settings, USD/URDF/MJCF files,
or checkpoints. It does not convert assets, embed a 3D viewport, tune policies,
choose a best checkpoint, run cloud jobs, kill unrelated processes, or create a
database. Large runs, checkpoints, videos, and evidence remain external.
