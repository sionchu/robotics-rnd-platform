# Robot Learning Workbench

Robot Learning Workbench is a dependency-light Windows desktop application for
understanding and operating trusted local robot-learning tasks. It is a thin
orchestration and teaching layer over a task workspace and an existing external
Isaac Lab installation. It is not an RL framework, task editor, or Isaac Sim
replacement.

## Architecture boundary

```text
WORKBENCH_ROOT: tkinter desktop process (standard library only)
        |
        | helper path + exact cwd/env/argv + subprocess + explicit JSON output
        v
isaac_probe.py through isaaclab.bat
        |
WORKSPACE_ROOT: registration module, task source, optional task commands
        |
        +-- Isaac Lab / Isaac Sim task configuration
        +-- native Isaac GUI
        +-- existing TensorBoard event reader
```

The three roots are independent: `WORKBENCH_ROOT` owns the application and its
helper, `WORKSPACE_ROOT` owns task code, and `ISAACLAB_ROOT` owns the simulator
runtime. The desktop process never imports Isaac Lab, Omni, USD, Torch, RSL-RL,
or TensorBoard. Machine paths and local task notes are stored under:

```text
%LOCALAPPDATA%\robot-learning-workbench\settings.json
```

No workstation path is written to repository files.

## Launch

From the repository root using its normal Python environment:

```powershell
.\.venv\Scripts\python.exe -m applications.robot_learning_workbench
```

Use **File > Open Workspace** to select trusted local task code and **File >
Configure Isaac Lab** to select an existing runtime. The application never
installs or repairs either environment.

## Trusted workspace contract

The Workbench only imports a registration module when you explicitly probe or
launch a task. A workspace is therefore trusted local code, not a sandbox.

Existing robotics-rnd workspaces may use:

```text
experiments/robot/<number>_<name>/registration.py
```

Standalone workspaces may instead contain `robot_learning_workbench_tasks.json`:

```json
{"tasks": [{"registration": "tasks/example/registration.py", "name": "Example"}]}
```

Each registration defines `TASK_ID`, optionally `PLAY_TASK_ID`, and may expose
task-local command scripts through the manifest. A workspace with neither form
opens normally and reports no discoverable tasks.

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
   Instantiated tasks attach ObservationManager dimensions by group and term
   name while retaining the verified total observation dimension.
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
classes, paths, raw metric names, and exact commands.

Isaac commands run with the Isaac Lab checkout as their working directory and
an explicit workspace `PYTHONPATH`, so generated training artifacts stay under
the external Isaac Lab run tree rather than the repository.

## Deliberate exclusions

V0 does not edit experiment source, rewards, PPO settings, USD/URDF/MJCF files,
or checkpoints. It does not convert assets, embed a 3D viewport, tune policies,
choose a best checkpoint, run cloud jobs, kill unrelated processes, or create a
database. Large runs, checkpoints, videos, and evidence remain external.
