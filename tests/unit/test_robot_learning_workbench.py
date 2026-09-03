from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

from applications.robot_learning_workbench.app import RobotLearningWorkbench
from applications.robot_learning_workbench.discovery import discover_tasks, parse_registration
from applications.robot_learning_workbench.isaac_probe import (
    _attach_runtime_observation_dimensions,
    _observation_unit,
)
from applications.robot_learning_workbench.models import (
    CommandSpec,
    EvaluationResult,
    MetricSeries,
    WorkbenchSettings,
    normalize_evaluation,
    observation_dimension_consistency,
    observation_term_rows,
    read_last_jsonl_record,
    sha256_file,
    transition_matrix,
)
from applications.robot_learning_workbench.process_runner import (
    ProcessRunner,
    build_experiment_script_command,
    build_probe_command,
    build_train_command,
    format_command,
    format_spec,
)


@pytest.mark.skipif(os.name != "nt", reason="Windows cmd.exe batch argument contract")
def test_windows_batch_transport_preserves_literal_arguments(tmp_path: Path) -> None:
    batch_dir = tmp_path / "batch path with spaces"
    batch_dir.mkdir()
    batch = batch_dir / "record arguments.cmd"
    received_path = batch_dir / "received.txt"
    sentinel = tmp_path / "sentinel.txt"
    expected = [
        "plain",
        "SAFE VALUE",
        "SAFE&VALUE",
        "SAFE|VALUE",
        "SAFE^VALUE",
        "SAFE%VALUE",
        "SAFE!VALUE",
        "SAFE(VALUE)",
        "SAFE<VALUE",
        "SAFE>VALUE",
        r"C:\Program Files\Robot Lab\asset.usd",
        "SAFE&echo.INJECTED>sentinel.txt",
        "TAIL",
    ]
    lines = [
        "@echo off",
        "setlocal DisableDelayedExpansion",
        'set "RLW_OUTPUT=%~dp0received.txt"',
    ]
    for index in range(len(expected)):
        lines.extend((f'set "RLW_CAPTURE_{index}=%~1"', "shift"))
    lines.append('> "%RLW_OUTPUT%" set RLW_CAPTURE_')
    batch.write_text("\n".join(lines) + "\n", encoding="utf-8")

    runner = ProcessRunner()
    runner.start(CommandSpec("batch boundary", (str(batch), *expected), tmp_path))
    assert runner.process is not None
    assert runner.process.wait(timeout=10) == 0

    received = {}
    for line in received_path.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator:
            received[int(name.removeprefix("RLW_CAPTURE_"))] = value
    assert [received[index] for index in range(len(expected))] == expected
    assert not sentinel.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows cmd.exe batch argument contract")
@pytest.mark.parametrize("value", ['SAFE"VALUE', "SAFE\rVALUE", "SAFE\nVALUE", "SAFE\0VALUE"])
def test_windows_batch_transport_rejects_unrepresentable_values(tmp_path: Path, value: str) -> None:
    batch = tmp_path / "must-not-run.cmd"
    batch.write_text("@echo off\nexit /b 0\n", encoding="utf-8")
    runner = ProcessRunner()

    with pytest.raises(RuntimeError, match="cannot contain"):
        runner.start(CommandSpec("invalid batch argument", (str(batch), value), tmp_path))
    assert runner.process is None


def _experiment_fixture(tmp_path: Path) -> Path:
    folder = tmp_path / "experiments" / "robot" / "123_safe_task"
    folder.mkdir(parents=True)
    (folder / "registration.py").write_text(
        """
TASK_ID = "Fixture-Task-v0"
PLAY_TASK_ID = "Fixture-Task-Play-v0"
RUNTIME_MODULE = "experiments.robot.fixture.runtime"
raise RuntimeError("AST discovery must never execute this module")

class FixtureEnvCfg:
    pass

class FixtureEnvCfg_PLAY:
    pass

class FixturePPORunnerCfg:
    pass
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (folder / "gui_probe.py").write_text("# fixture\n", encoding="utf-8")
    return folder


def test_ast_discovery_does_not_execute_experiment_source(tmp_path: Path) -> None:
    folder = _experiment_fixture(tmp_path)
    metadata = parse_registration(folder / "registration.py")
    experiments = discover_tasks(tmp_path)

    assert metadata["TASK_ID"] == "Fixture-Task-v0"
    assert len(experiments) == 1
    assert experiments[0].task_id == "Fixture-Task-v0"
    assert experiments[0].play_task_id == "Fixture-Task-Play-v0"
    assert experiments[0].env_config_class == "FixtureEnvCfg"
    assert experiments[0].play_config_class == "FixtureEnvCfg_PLAY"
    assert experiments[0].ppo_config_class == "FixturePPORunnerCfg"
    assert experiments[0].scripts["gui"] == folder / "gui_probe.py"


def test_training_command_is_explicit_and_uses_external_callback(tmp_path: Path) -> None:
    experiment = discover_tasks(tmp_path)[0] if (tmp_path / "experiments").exists() else None
    if experiment is None:
        _experiment_fixture(tmp_path)
        experiment = discover_tasks(tmp_path)[0]
    spec = build_train_command(
        workspace_root=tmp_path,
        isaac_lab_root=tmp_path / "IsaacLab",
        experiment=experiment,
        num_envs=64,
        iterations=5,
        seed=42,
        device="cuda:0",
        run_name="smoke seed 42",
    )

    assert spec.argv[0].endswith("isaaclab.bat")
    assert spec.argv[1] == "train"
    assert spec.argv[spec.argv.index("--max_iterations") + 1] == "5"
    assert spec.argv[spec.argv.index("--external_callback") + 1].endswith(".register_tasks")
    assert "--headless" in spec.argv
    assert '"smoke seed 42"' in format_command(spec.argv)
    assert spec.cwd == tmp_path / "IsaacLab"
    assert spec.environment == {"PYTHONPATH": str(tmp_path)}
    assert format_spec(spec).startswith(f'cd /d {tmp_path / "IsaacLab"} && set "PYTHONPATH={tmp_path}" && ')

    runner = build_experiment_script_command(
        workspace_root=tmp_path,
        isaac_lab_root=tmp_path / "IsaacLab",
        experiment=experiment,
        role="gui",
        arguments=["--seed", "42"],
    )
    assert runner is not None
    assert runner.argv[-2:] == ("--seed", "42")
    assert runner.cwd == tmp_path / "IsaacLab"


def test_manifest_workspace_is_independent_from_workbench_root(tmp_path: Path) -> None:
    workbench_root = tmp_path / "workbench source"
    helper = workbench_root / "applications" / "robot_learning_workbench" / "isaac_probe.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("# workbench-owned helper\n", encoding="utf-8")
    workspace_root = tmp_path / "trusted task workspace with spaces"
    registration = workspace_root / "tasks" / "sample" / "registration.py"
    registration.parent.mkdir(parents=True)
    (workspace_root / "tasks" / "__init__.py").write_text("", encoding="utf-8")
    (registration.parent / "__init__.py").write_text("", encoding="utf-8")
    registration.write_text('TASK_ID = "External-Fixture-v0"\n', encoding="utf-8")
    (workspace_root / "robot_learning_workbench_tasks.json").write_text(
        json.dumps({"tasks": [{"name": "External fixture", "registration": "tasks/sample/registration.py"}]}),
        encoding="utf-8",
    )

    tasks = discover_tasks(workspace_root)
    assert len(tasks) == 1
    assert tasks[0].registration_module == "tasks.sample.registration"
    spec = build_probe_command(
        workbench_root=workbench_root,
        workspace_root=workspace_root,
        isaac_lab_root=tmp_path / "IsaacLab",
        experiment=tasks[0],
        output_path=tmp_path / "probe.json",
        device="cuda:0",
        instantiate=False,
    )

    assert spec.argv[2] == str(helper)
    assert (
        str(workspace_root / "applications" / "robot_learning_workbench" / "isaac_probe.py") not in spec.argv
    )
    assert spec.environment == {"PYTHONPATH": str(workspace_root)}


def test_no_task_workspace_discovers_nothing(tmp_path: Path) -> None:
    workspace_root = tmp_path / "empty workspace"
    workspace_root.mkdir()
    assert discover_tasks(workspace_root) == []


def test_settings_round_trip_stays_at_explicit_external_path(tmp_path: Path) -> None:
    path = tmp_path / "local" / "settings.json"
    settings = WorkbenchSettings(workspace_root="C:/workspace", presentation_mode="engineering")
    settings.asset_catalog.append({"path": "D:/asset.usd", "type": ".usd"})
    settings.save(path)

    loaded = WorkbenchSettings.load(path)
    assert loaded.workspace_root == "C:/workspace"
    assert loaded.presentation_mode == "engineering"
    assert loaded.asset_catalog == [{"path": "D:/asset.usd", "type": ".usd"}]


def test_evaluation_normalization_and_transition_matrix(tmp_path: Path) -> None:
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    first_path.write_text(
        json.dumps(
            {
                "experiment": "A",
                "episodes": 2,
                "successes": 1,
                "success_rate": 0.5,
                "failure_taxonomy": {"TASK_SPECIFIC": 1},
                "paired_episode_records": [
                    {"episode_id": "env_00_ep_00", "success": True},
                    {"episode_id": "env_00_ep_01", "success": False},
                ],
            }
        ),
        encoding="utf-8",
    )
    second_path.write_text(
        json.dumps(
            {
                "experiment": "B",
                "episodes": 2,
                "successes": 1,
                "paired_episode_records": [
                    {"episode_id": "env_00_ep_00", "success": False},
                    {"episode_id": "env_00_ep_01", "success": True},
                ],
            }
        ),
        encoding="utf-8",
    )

    first = normalize_evaluation(first_path)
    second = normalize_evaluation(second_path)
    matrix = transition_matrix(first, second)

    assert first.taxonomy == {"TASK_SPECIFIC": 1}
    assert "mean_final_xy_error_mm" not in first.metrics
    assert matrix["A SUCCESS -> B FAILURE"] == 1
    assert matrix["A FAILURE -> B SUCCESS"] == 1


def test_transition_matrix_uses_only_shared_stable_ids(tmp_path: Path) -> None:
    empty = EvaluationResult(tmp_path, "x", None, None, None, None, None, {}, {}, {}, {}, {})
    other = EvaluationResult(
        tmp_path,
        "y",
        None,
        None,
        1,
        1,
        0,
        {},
        {},
        {},
        {"env_00_ep_00": {"success": True}},
        {},
    )
    assert sum(transition_matrix(empty, other).values()) == 0


def test_metric_series_keeps_raw_values() -> None:
    series = MetricSeries.from_json(
        "Policy/mean_std", [{"step": 0, "value": 1.0}, {"step": 10, "value": 0.25}]
    )
    assert series.first_last() == (1.0, 0.25)


def test_unknown_observation_units_are_task_defined() -> None:
    assert _observation_unit() == "task-defined"
    assert _observation_unit() != "m"
    assert _observation_unit() != "m/s"


def test_runtime_probe_associates_observation_dimensions_by_group_and_name() -> None:
    groups = [
        {
            "group": "policy",
            "terms": [
                {
                    "name": "joint_pos",
                    "meaning": "joint position",
                    "unit": "task-defined",
                    "source": "Task Config",
                },
                {
                    "name": "joint_vel",
                    "meaning": "joint velocity",
                    "unit": "task-defined",
                    "source": "Task Config",
                },
            ],
        },
        {
            "group": "critic",
            "terms": [
                {
                    "name": "joint_pos",
                    "meaning": "critic joint position",
                    "unit": "task-defined",
                    "source": "Task Config",
                }
            ],
        },
    ]
    manager = type(
        "FakeObservationManager",
        (),
        {
            "active_terms": {"policy": ["joint_vel", "joint_pos"], "critic": ["joint_pos"]},
            "group_obs_term_dim": {"policy": [(3,), (1,)], "critic": [(2,)]},
        },
    )()

    diagnostics = _attach_runtime_observation_dimensions(groups, manager)
    rows = observation_term_rows(groups)

    assert diagnostics == []
    assert [row[0] for row in rows] == [
        "Policy / joint_pos",
        "Policy / joint_vel",
        "Critic / joint_pos",
    ]
    assert [row[1].split(";", 1)[0] for row in rows] == ["dim=1", "dim=3", "dim=2"]
    assert all(row[2] == "task-defined" for row in rows)
    assert all(row[3] == "Runtime ObservationManager" for row in rows)


def test_observation_dimension_unavailable_without_runtime_manager_data() -> None:
    groups = [
        {
            "group": "policy",
            "terms": [
                {
                    "name": "unknown",
                    "dimension": None,
                    "meaning": "unresolved",
                    "unit": "",
                    "source": "Task Config",
                }
            ],
        }
    ]
    manager = type(
        "UnavailableObservationManager",
        (),
        {"active_terms": {}, "group_obs_term_dim": {}},
    )()

    diagnostics = _attach_runtime_observation_dimensions(groups, manager)
    rows = observation_term_rows(groups)

    assert diagnostics == ["Runtime observation dimensions are unavailable for group 'policy'."]
    assert rows[0][1].startswith("dim=N/A — runtime probe required;")
    assert rows[0][3] == "Task Config"


def test_observation_dimension_sum_consistency() -> None:
    groups = [
        {
            "group": "policy",
            "terms": [{"dimension": dimension} for dimension in (3, 3, 3, 1)],
        }
    ]

    assert observation_dimension_consistency(groups, "policy", 10) is None
    assert observation_dimension_consistency(groups, "policy", 9) == (
        "MISMATCH: observation term sum 10 does not equal runtime policy total 9."
    )


def test_task_mdp_observation_rows_render_supplied_dimensions_and_total() -> None:
    workbench = RobotLearningWorkbench.__new__(RobotLearningWorkbench)
    workbench.probe_data = {
        "observations": [
            {
                "group": "policy",
                "terms": [
                    {
                        "name": name,
                        "dimension": dimension,
                        "dimension_source": "Runtime ObservationManager",
                        "meaning": name,
                        "unit": "values",
                    }
                    for name, dimension in (
                        ("joint_pos", 3),
                        ("joint_vel", 3),
                        ("previous_action", 3),
                        ("task_scalar", 1),
                    )
                ],
            }
        ],
        "runtime": {"policy_observation_shape": [1, 10]},
    }

    rows = workbench._mdp_rows("Observation")

    assert [(row[0], row[1].split(";", 1)[0]) for row in rows[:-1]] == [
        ("joint_pos", "dim=3"),
        ("joint_vel", "dim=3"),
        ("previous_action", "dim=3"),
        ("task_scalar", "dim=1"),
    ]
    assert rows[-1] == ("Total", "10", "values", "Runtime Probe")


def test_raw_three_value_action_has_no_derived_xyz_millimetre_row() -> None:
    class FakeTelemetryTree:
        def __init__(self) -> None:
            self.rows: list[tuple[str, tuple[str, str]]] = []

        def delete(self, *_items: str) -> None:
            self.rows.clear()

        def get_children(self) -> tuple[str, ...]:
            return ()

        def insert(self, _parent: str, _index: str, *, text: str, values: tuple[str, str]) -> None:
            self.rows.append((text, values))

    workbench = RobotLearningWorkbench.__new__(RobotLearningWorkbench)
    workbench.telemetry_tree = FakeTelemetryTree()
    workbench.probe_data = {"actions": [{"scale": 0.005}]}

    workbench._render_telemetry({"action": [0.2, -0.1, -0.5]})

    assert ("action", ("[0.2, -0.1, -0.5]", "External JSONL")) in workbench.telemetry_tree.rows
    assert all("physical_delta_xyz_mm" not in name for name, _values in workbench.telemetry_tree.rows)


def test_jsonl_tail_reader_returns_latest_complete_object(tmp_path: Path) -> None:
    telemetry = tmp_path / "episode.jsonl"
    telemetry.write_text(
        '{"step": 1, "success": false}\nnot-json\n{"step": 2, "state": {"xy_error_m": 0.00322}}\n{"step":',
        encoding="utf-8",
    )

    assert read_last_jsonl_record(telemetry) == {
        "step": 2,
        "state": {"xy_error_m": 0.00322},
    }


def test_checkpoint_hash_and_desktop_import_boundary(tmp_path: Path) -> None:
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"frozen policy")
    assert sha256_file(checkpoint) == "24E3B7979600C734D7580E238A2EF4722947AA911686313B54597CF19ACE351D"

    package = Path("applications/robot_learning_workbench")
    forbidden = {"isaaclab", "omni", "pxr", "torch", "rsl_rl", "tensorboard"}
    for source in package.glob("*.py"):
        if source.name == "isaac_probe.py":
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        imported = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported.update(
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        assert imported.isdisjoint(forbidden), f"forbidden desktop import in {source}: {imported}"
