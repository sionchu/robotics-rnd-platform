from __future__ import annotations

import ast
import json
from pathlib import Path

from applications.robot_learning_workbench.app import RobotLearningWorkbench
from applications.robot_learning_workbench.discovery import discover_experiments, parse_registration
from applications.robot_learning_workbench.isaac_probe import _attach_runtime_observation_dimensions
from applications.robot_learning_workbench.models import (
    EvaluationResult,
    MetricSeries,
    WorkbenchSettings,
    explain_reward_gate,
    normalize_evaluation,
    normalized_to_physical,
    observation_dimension_consistency,
    observation_term_rows,
    read_last_jsonl_record,
    sha256_file,
    transition_matrix,
)
from applications.robot_learning_workbench.process_runner import (
    build_experiment_script_command,
    build_train_command,
    format_command,
    format_spec,
)


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
    experiments = discover_experiments(tmp_path)

    assert metadata["TASK_ID"] == "Fixture-Task-v0"
    assert len(experiments) == 1
    assert experiments[0].task_id == "Fixture-Task-v0"
    assert experiments[0].play_task_id == "Fixture-Task-Play-v0"
    assert experiments[0].env_config_class == "FixtureEnvCfg"
    assert experiments[0].play_config_class == "FixtureEnvCfg_PLAY"
    assert experiments[0].ppo_config_class == "FixturePPORunnerCfg"
    assert experiments[0].scripts["gui"] == folder / "gui_probe.py"


def test_training_command_is_explicit_and_uses_external_callback(tmp_path: Path) -> None:
    experiment = discover_experiments(tmp_path)[0] if (tmp_path / "experiments").exists() else None
    if experiment is None:
        _experiment_fixture(tmp_path)
        experiment = discover_experiments(tmp_path)[0]
    spec = build_train_command(
        repo_root=tmp_path,
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
        repo_root=tmp_path,
        isaac_lab_root=tmp_path / "IsaacLab",
        experiment=experiment,
        role="gui",
        arguments=["--seed", "42"],
    )
    assert runner is not None
    assert runner.argv[-2:] == ("--seed", "42")
    assert runner.cwd == tmp_path / "IsaacLab"


def test_settings_round_trip_stays_at_explicit_external_path(tmp_path: Path) -> None:
    path = tmp_path / "local" / "settings.json"
    settings = WorkbenchSettings(repo_root="C:/repo", presentation_mode="engineering")
    settings.asset_catalog.append({"path": "D:/asset.usd", "type": ".usd"})
    settings.save(path)

    loaded = WorkbenchSettings.load(path)
    assert loaded.repo_root == "C:/repo"
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


def test_metric_series_and_action_conversion() -> None:
    series = MetricSeries.from_json(
        "Policy/mean_std", [{"step": 0, "value": 1.0}, {"step": 10, "value": 0.25}]
    )
    assert series.first_last() == (1.0, 0.25)
    assert normalized_to_physical([0.2, -0.1, -0.5], 0.005) == [0.001, -0.0005, -0.0025]


def test_runtime_probe_associates_observation_dimensions_by_group_and_name() -> None:
    groups = [
        {
            "group": "policy",
            "terms": [
                {"name": "depth", "meaning": "depth", "unit": "m", "source": "Task Config"},
                {"name": "position", "meaning": "position", "unit": "m", "source": "Task Config"},
            ],
        },
        {
            "group": "critic",
            "terms": [
                {"name": "position", "meaning": "critic position", "unit": "m", "source": "Task Config"}
            ],
        },
    ]
    manager = type(
        "FakeObservationManager",
        (),
        {
            "active_terms": {"policy": ["position", "depth"], "critic": ["position"]},
            "group_obs_term_dim": {"policy": [(3,), (1,)], "critic": [(2,)]},
        },
    )()

    diagnostics = _attach_runtime_observation_dimensions(groups, manager)
    rows = observation_term_rows(groups)

    assert diagnostics == []
    assert [row[0] for row in rows] == [
        "Policy / depth",
        "Policy / position",
        "Critic / position",
    ]
    assert [row[1].split(";", 1)[0] for row in rows] == ["dim=1", "dim=3", "dim=2"]
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
                        ("peg_pos_rel_hole", 3),
                        ("peg_linear_velocity", 3),
                        ("previous_action", 3),
                        ("insertion_depth", 1),
                    )
                ],
            }
        ],
        "runtime": {"policy_observation_shape": [1, 10]},
    }

    rows = workbench._mdp_rows("Observation")

    assert [(row[0], row[1].split(";", 1)[0]) for row in rows[:-1]] == [
        ("peg_pos_rel_hole", "dim=3"),
        ("peg_linear_velocity", "dim=3"),
        ("previous_action", "dim=3"),
        ("insertion_depth", "dim=1"),
    ]
    assert rows[-1] == ("Total", "10", "values", "Runtime Probe")


def test_reward_gate_explanation_is_deterministic() -> None:
    outside = explain_reward_gate(
        reward_name="axial", xy_error_m=0.00322, gate_threshold_m=0.003, raw_value=0.0
    )
    inside = explain_reward_gate(
        reward_name="axial", xy_error_m=0.002, gate_threshold_m=0.003, raw_value=0.0004
    )
    assert "3.22 mm" in outside and "outside" in outside
    assert "gate is ON" in inside and "+0.000400" in inside


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
