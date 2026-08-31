"""Narrow Isaac-aware helper for task probing, GUI runs, and TensorBoard reads.

This file is launched through ``isaaclab.bat -p``.  The normal workbench
desktop process never imports it, so Isaac, Omni, Torch, and RSL-RL stay across
the subprocess/JSON boundary.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path
from typing import Any


def _preparse_mode() -> str:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--mode", choices=("task", "gui", "metrics"), required=True)
    return parser.parse_known_args()[0].mode


def _base_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--mode", choices=("task", "gui", "metrics"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--registration", default="")
    parser.add_argument("--task", default="")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--instantiate", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=600)
    return parser


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _metrics_main() -> int:
    parser = _base_parser("Read TensorBoard scalar evidence")
    args = parser.parse_args()
    if args.run_dir is None or not args.run_dir.is_dir():
        parser.error("--run-dir must be an existing directory for metrics mode")
    from tensorboard.backend.event_processing.event_accumulator import (  # type: ignore[import-not-found]
        EventAccumulator,
    )

    event_files = sorted(args.run_dir.glob("events.out.tfevents.*"), key=lambda path: path.stat().st_mtime)
    if not event_files:
        raise FileNotFoundError(f"No TensorBoard event file under {args.run_dir}")
    event_file = event_files[-1]
    accumulator = EventAccumulator(str(event_file), size_guidance={"scalars": 0})
    accumulator.Reload()
    series = {
        tag: [
            {"step": int(event.step), "value": float(event.value), "wall_time": float(event.wall_time)}
            for event in accumulator.Scalars(tag)
        ]
        for tag in accumulator.Tags().get("scalars", [])
    }
    payload = {
        "schema_version": 1,
        "source": "TensorBoard event file",
        "run_dir": str(args.run_dir),
        "event_file": str(event_file),
        "series": series,
    }
    _write(args.output, payload)
    return 0


def _isaac_main() -> int:
    from isaaclab.app import AppLauncher  # type: ignore[import-not-found]

    parser = _base_parser("Probe or display one registered Isaac Lab task")
    AppLauncher.add_app_launcher_args(parser)
    args = parser.parse_args()
    if not args.registration or not args.task:
        parser.error("--registration and --task are required for task/gui mode")
    app_launcher = AppLauncher(vars(args))
    simulation_app = app_launcher.app
    env: Any = None
    try:
        import gymnasium as gym  # type: ignore[import-not-found]
        import torch
        from isaaclab_tasks.utils import parse_env_cfg  # type: ignore[import-not-found]

        registration = importlib.import_module(args.registration)
        registration.register_tasks()
        spec = gym.spec(args.task)
        device = args.device or "cuda:0"
        env_cfg = parse_env_cfg(args.task, device=device, num_envs=1 if args.mode == "gui" else None)
        env_cfg.env_name = args.task
        env_cfg.seed = args.seed
        env_cfg.sim.device = device
        if args.mode == "gui":
            env_cfg.scene.num_envs = 1
        payload = _task_payload(args, registration, spec, env_cfg)
        if args.instantiate or args.mode == "gui":
            env_cfg.scene.num_envs = 1
            env = gym.make(args.task, cfg=env_cfg).unwrapped
            observations, _ = env.reset(seed=args.seed)
            payload["runtime"] = _runtime_payload(env, observations)
        if args.mode == "gui":
            started = time.perf_counter()
            steps_run = 0
            while steps_run < args.steps and simulation_app.is_running():
                action = torch.zeros((env.num_envs, env.action_manager.total_action_dim), device=env.device)
                with torch.inference_mode():
                    env.step(action)
                steps_run += 1
            payload["gui"] = {
                "steps_requested": args.steps,
                "steps_run": steps_run,
                "elapsed_s": time.perf_counter() - started,
                "visual_reviewed": False,
            }
        _write(args.output, payload)
        return 0
    finally:
        if env is not None:
            env.close()
        simulation_app.close()


def _task_payload(args: Any, registration: Any, spec: Any, env_cfg: Any) -> dict[str, Any]:
    play_task = getattr(registration, "PLAY_TASK_ID", None)
    kwargs = dict(spec.kwargs or {})
    constants = {
        name: _resolve_constant(registration, name)
        for name in (
            "PEG_WIDTH",
            "PEG_LENGTH",
            "HOLE_INNER",
            "ACTION_SCALE_M",
            "ALIGNMENT_GATE_M",
            "SUCCESS_LATERAL_M",
            "SUCCESS_DEPTH_M",
            "RESET_XY_OFFSET_M",
            "APPROACH_HEIGHT_M",
            "HOLE_OFFSET_X_RANGE_M",
            "HOLE_OFFSET_Y_RANGE_M",
        )
    }
    action_terms = _manager_terms(env_cfg.actions)
    observation_groups = _observation_groups(env_cfg.observations)
    rewards = _reward_terms(env_cfg.rewards, constants)
    return {
        "schema_version": 1,
        "source": "Runtime Probe",
        "task": {
            "task_id": args.task,
            "play_task_id": play_task,
            "registration_module": args.registration,
            "env_entry_point": spec.entry_point,
            "env_config_entry_point": kwargs.get("env_cfg_entry_point"),
            "ppo_config_entry_point": kwargs.get("rsl_rl_cfg_entry_point"),
            "episode_length_s": _number(getattr(env_cfg, "episode_length_s", None)),
            "physics_dt_s": _number(getattr(env_cfg.sim, "dt", None)),
            "decimation": _number(getattr(env_cfg, "decimation", None)),
            "control_dt_s": _control_dt(env_cfg),
            "default_num_envs": _number(getattr(env_cfg.scene, "num_envs", None)),
            "seed": _number(getattr(env_cfg, "seed", None)),
            "device": str(getattr(env_cfg.sim, "device", args.device or "cuda:0")),
        },
        "constants": constants,
        "assets": _scene_assets(env_cfg.scene),
        "observations": observation_groups,
        "actions": action_terms,
        "rewards": rewards,
        "terminations": _termination_terms(env_cfg.terminations, constants),
        "resets": _reset_terms(env_cfg.events, constants),
        "ppo": _ppo_payload(kwargs.get("rsl_rl_cfg_entry_point")),
    }


def _runtime_payload(env: Any, observations: Any) -> dict[str, Any]:
    import torch

    policy = observations.get("policy") if isinstance(observations, dict) else observations
    observation_dims: dict[str, Any] = {}
    manager = env.observation_manager
    group_dims = getattr(manager, "group_obs_term_dim", {})
    if isinstance(group_dims, dict):
        observation_dims = {str(key): _json_value(value) for key, value in group_dims.items()}
    action_terms = []
    for name, term in zip(env.action_manager.active_terms, env.action_manager._terms, strict=False):
        action_terms.append({"name": name, "dimension": int(getattr(term, "action_dim", 0))})
    return {
        "observation_space": str(env.observation_space),
        "action_space": str(env.action_space),
        "policy_observation_shape": (
            list(policy.shape) if policy is not None and hasattr(policy, "shape") else None
        ),
        "policy_observation_finite": (
            bool(torch.isfinite(policy).all().item()) if policy is not None else False
        ),
        "observation_term_dimensions": observation_dims,
        "action_dimension": int(env.action_manager.total_action_dim),
        "action_terms": action_terms,
        "max_episode_length": int(env.max_episode_length),
        "step_dt_s": float(env.step_dt),
    }


def _scene_assets(scene: Any) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for name, value in _public_items(scene):
        if not hasattr(value, "prim_path"):
            continue
        class_name = type(value).__name__
        spawn = getattr(value, "spawn", None)
        source = _asset_source(spawn)
        assets.append(
            {
                "name": name,
                "category": _asset_category(name, class_name),
                "config_class": f"{type(value).__module__}.{class_name}",
                "prim_path": str(getattr(value, "prim_path", "")),
                "source_type": type(spawn).__name__ if spawn is not None else "configured",
                "source": source,
                "fixed_base": _nested_value(spawn, "articulation_props", "fix_root_link"),
                "dimensions": _json_value(getattr(spawn, "size", None)),
                "default_pose": _pose_payload(getattr(value, "init_state", None)),
                "role": _asset_role(name),
                "status": "CONFIGURED",
            }
        )
    return assets


def _observation_groups(observations: Any) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for group_name, group in _public_items(observations):
        terms = []
        for name, cfg in _public_items(group):
            if not hasattr(cfg, "func"):
                continue
            terms.append(
                {
                    "name": name,
                    "function": _callable_name(cfg.func),
                    "dimension": None,
                    "unit": _observation_unit(name),
                    "meaning": _observation_meaning(name),
                    "source": "Task Config",
                }
            )
        if terms:
            groups.append(
                {
                    "group": group_name,
                    "concatenate_terms": bool(getattr(group, "concatenate_terms", False)),
                    "corruption_enabled": bool(getattr(group, "enable_corruption", False)),
                    "terms": terms,
                }
            )
    return groups


def _manager_terms(config: Any) -> list[dict[str, Any]]:
    terms: list[dict[str, Any]] = []
    for name, cfg in _public_items(config):
        class_name = type(cfg).__name__
        if not class_name.endswith("ActionCfg") and "Action" not in class_name:
            continue
        controller = getattr(cfg, "controller", None)
        terms.append(
            {
                "name": name,
                "config_class": f"{type(cfg).__module__}.{class_name}",
                "dimension": None,
                "controller_type": type(controller).__name__ if controller is not None else class_name,
                "command_type": getattr(controller, "command_type", None),
                "scale": _json_value(getattr(cfg, "scale", None)),
                "relative": getattr(controller, "use_relative_mode", None),
                "asset_name": getattr(cfg, "asset_name", None),
                "body_name": getattr(cfg, "body_name", None),
                "joint_names": _json_value(getattr(cfg, "joint_names", None)),
                "ik_method": getattr(controller, "ik_method", None),
                "ik_parameters": _json_value(getattr(controller, "ik_params", None)),
                "source": "Task Config",
            }
        )
    return terms


def _reward_terms(config: Any, constants: dict[str, Any]) -> list[dict[str, Any]]:
    terms = []
    for name, cfg in _public_items(config):
        if not hasattr(cfg, "func") or not hasattr(cfg, "weight"):
            continue
        gate = None
        if "success_aligned_axial" in name:
            gate = {"state": "xy_error_m", "operator": "<=", "threshold": constants["SUCCESS_LATERAL_M"]}
        elif "axial" in name or "insertion_progress" in name:
            gate = {"state": "xy_error_m", "operator": "<=", "threshold": constants["ALIGNMENT_GATE_M"]}
        terms.append(
            {
                "name": name,
                "weight": float(cfg.weight),
                "function": _callable_name(cfg.func),
                "gate": gate,
                "source": "Task Config" if gate is None else "Runtime Probe",
            }
        )
    return terms


def _termination_terms(config: Any, constants: dict[str, Any]) -> list[dict[str, Any]]:
    terms = []
    for name, cfg in _public_items(config):
        if not hasattr(cfg, "func"):
            continue
        thresholds = None
        if name == "success":
            thresholds = {
                "xy_error_m_max": constants["SUCCESS_LATERAL_M"],
                "insertion_depth_m_min": constants["SUCCESS_DEPTH_M"],
            }
        terms.append(
            {
                "name": name,
                "function": _callable_name(cfg.func),
                "timeout": bool(getattr(cfg, "time_out", False)),
                "thresholds": thresholds,
                "source": "Runtime Probe" if thresholds else "Task Config",
            }
        )
    return terms


def _reset_terms(config: Any, constants: dict[str, Any]) -> list[dict[str, Any]]:
    terms = []
    ranges = {
        "hole_x_m": constants["HOLE_OFFSET_X_RANGE_M"],
        "hole_y_m": constants["HOLE_OFFSET_Y_RANGE_M"],
        "peg_relative_xy_m": (
            -constants["RESET_XY_OFFSET_M"],
            constants["RESET_XY_OFFSET_M"],
        )
        if isinstance(constants["RESET_XY_OFFSET_M"], int | float)
        else None,
        "approach_height_m": constants["APPROACH_HEIGHT_M"],
    }
    for name, cfg in _public_items(config):
        if not hasattr(cfg, "func"):
            continue
        terms.append(
            {
                "name": name,
                "mode": getattr(cfg, "mode", None),
                "function": _callable_name(cfg.func),
                "ranges": ranges,
                "source": "Runtime Probe",
            }
        )
    return terms


def _ppo_payload(entry_point: Any) -> dict[str, Any] | None:
    if not isinstance(entry_point, str) or ":" not in entry_point:
        return None
    module_name, class_name = entry_point.split(":", 1)
    cfg = getattr(importlib.import_module(module_name), class_name)()
    algorithm = getattr(cfg, "algorithm", None)
    actor = getattr(cfg, "actor", None)
    critic = getattr(cfg, "critic", None)
    distribution = getattr(actor, "distribution_cfg", None)
    return {
        "config_class": entry_point,
        "num_steps_per_env": _number(getattr(cfg, "num_steps_per_env", None)),
        "max_iterations": _number(getattr(cfg, "max_iterations", None)),
        "save_interval": _number(getattr(cfg, "save_interval", None)),
        "experiment_name": getattr(cfg, "experiment_name", None),
        "actor_hidden_dims": _json_value(getattr(actor, "hidden_dims", None)),
        "critic_hidden_dims": _json_value(getattr(critic, "hidden_dims", None)),
        "activation": getattr(actor, "activation", None),
        "initial_std": _number(getattr(distribution, "init_std", None)),
        "learning_rate": _number(getattr(algorithm, "learning_rate", None)),
        "schedule": getattr(algorithm, "schedule", None),
        "gamma": _number(getattr(algorithm, "gamma", None)),
        "lambda": _number(getattr(algorithm, "lam", None)),
        "clip": _number(getattr(algorithm, "clip_param", None)),
        "entropy": _number(getattr(algorithm, "entropy_coef", None)),
        "desired_kl": _number(getattr(algorithm, "desired_kl", None)),
        "source": "Task Config",
    }


def _public_items(value: Any) -> list[tuple[str, Any]]:
    items = vars(value).items() if hasattr(value, "__dict__") else []
    return [(name, item) for name, item in items if not name.startswith("_") and item is not None]


def _resolve_constant(module: Any, name: str) -> Any:
    visited: set[int] = set()
    current = module
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if hasattr(current, name):
            return _json_value(getattr(current, name))
        current = getattr(current, "base", None)
    return None


def _asset_source(spawn: Any) -> str | None:
    if spawn is None:
        return None
    for name in ("usd_path", "urdf_path", "mjcf_path", "asset_path", "filename"):
        value = getattr(spawn, name, None)
        if value:
            return str(value)
    return "generated primitive" if "Cuboid" in type(spawn).__name__ else None


def _asset_category(name: str, class_name: str) -> str:
    text = f"{name} {class_name}".lower()
    if "sensor" in text or "contact" in text:
        return "sensor"
    if "articulation" in text or name == "robot":
        return "articulation"
    if "rigid" in text:
        return "rigid object"
    if "marker" in text:
        return "marker"
    return "other"


def _asset_role(name: str) -> str:
    lowered = name.lower()
    if name == "robot":
        return "Robot"
    if lowered == "peg":
        return "Manipulated Object"
    if "contact" in lowered or "sensor" in lowered:
        return "Sensor"
    if "marker" in lowered:
        return "Marker"
    if any(token in lowered for token in ("plate", "wall", "fixture")):
        return "Fixture"
    return "Scene"


def _observation_unit(name: str) -> str:
    lowered = name.lower()
    if "velocity" in lowered:
        return "m/s"
    if "position" in lowered or "pos" in lowered or "depth" in lowered:
        return "m"
    if "action" in lowered:
        return "normalized"
    return "unspecified"


def _observation_meaning(name: str) -> str:
    meanings = {
        "peg_pos_rel_hole": "Peg position relative to the current hole target.",
        "peg_linear_velocity": "Current peg linear velocity.",
        "previous_action": "Policy action applied on the previous control step.",
        "insertion_depth": "Current axial insertion depth below the hole top.",
    }
    return meanings.get(name, "No workbench explanation is registered for this term.")


def _callable_name(value: Any) -> str:
    module = getattr(value, "__module__", type(value).__module__)
    name = getattr(value, "__qualname__", getattr(value, "__name__", type(value).__name__))
    return f"{module}.{name}"


def _pose_payload(state: Any) -> dict[str, Any] | None:
    if state is None:
        return None
    return {
        "position_m": _json_value(getattr(state, "pos", None)),
        "rotation_xyzw": _json_value(getattr(state, "rot", None)),
    }


def _nested_value(value: Any, *names: str) -> Any:
    current = value
    for name in names:
        current = getattr(current, name, None)
        if current is None:
            return None
    return _json_value(current)


def _control_dt(env_cfg: Any) -> float | None:
    dt = _number(getattr(env_cfg.sim, "dt", None))
    decimation = _number(getattr(env_cfg, "decimation", None))
    if isinstance(dt, int | float) and isinstance(decimation, int | float):
        return float(dt * decimation)
    return None


def _number(value: Any) -> int | float | None:
    return value if isinstance(value, int | float) else None


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if hasattr(value, "tolist"):
        return value.tolist()
    return str(value)


def main() -> int:
    return _metrics_main() if _preparse_mode() == "metrics" else _isaac_main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ROBOT_LEARNING_WORKBENCH_HELPER_ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        raise
