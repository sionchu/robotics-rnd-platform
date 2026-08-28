"""Finite Experiment 020 runtime, baseline, and policy evaluations."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata as metadata
import json
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher

PAIRED_PLAN_SHA256 = "ece1662c6b5de3016c77b67c667b75f37551b3de80eaf137897645576abd2f2c"

parser = argparse.ArgumentParser(description="Experiment 020 finite evaluation")
parser.add_argument("--mode", choices=("runtime", "oracle", "random", "paired", "holdout"), required=True)
parser.add_argument("--task", default="Isaac-UR10e-PegInsert-StatePrecision-v1")
parser.add_argument("--checkpoint", type=Path)
parser.add_argument("--num_envs", type=int, default=64)
parser.add_argument("--episodes", type=int, default=128)
parser.add_argument("--episodes-per-env", type=int, default=4)
parser.add_argument("--paired-reset-seed", type=int, default=43)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--steps", type=int, default=30)
parser.add_argument("--output", type=Path, required=True)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
app_launcher = AppLauncher(vars(args))
simulation_app = app_launcher.app


def checkpoint_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def build_reset_plan(seed: int, num_envs: int, episodes_per_env: int) -> tuple[dict[str, Any], str]:
    """Reproduce the Experiment 019 env-major plan without simulator RNG."""

    generator = random.Random(seed)
    plan: list[list[dict[str, Any]]] = []
    for env_id in range(num_envs):
        env_plan: list[dict[str, Any]] = []
        for episode_index in range(episodes_per_env):
            env_plan.append(
                {
                    "env_id": env_id,
                    "episode_index": episode_index,
                    "hole_offset_x_mm": round(generator.uniform(-40.0, 40.0), 6),
                    "hole_offset_y_mm": round(generator.uniform(-30.0, 30.0), 6),
                    "peg_initial_offset_x_mm": round(generator.uniform(-15.0, 15.0), 6),
                    "peg_initial_offset_y_mm": round(generator.uniform(-15.0, 15.0), 6),
                }
            )
        plan.append(env_plan)
    document = {
        "seed": seed,
        "generator": (
            "Python random.Random(seed) MT19937; env-major; four uniform draws per episode; "
            "values rounded to 1e-6 mm"
        ),
        "units": "mm",
        "num_envs": num_envs,
        "episodes_per_env": episodes_per_env,
        "plan": plan,
    }
    serialized = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return document, hashlib.sha256(serialized).hexdigest()


def region_for_offset(offset_xy_m: list[float]) -> str:
    x_mm, y_mm = offset_xy_m[0] * 1000.0, offset_xy_m[1] * 1000.0
    if abs(x_mm) <= 20.0 and abs(y_mm) <= 15.0:
        return "center"
    if abs(x_mm) / 40.0 >= abs(y_mm) / 30.0:
        return "left" if x_mm < 0.0 else "right"
    return "backward" if y_mm < 0.0 else "forward"


def deterministic_insertion_oracle(env: Any, learning_lab: Any) -> Any:
    """Use only the task's state to align tightly before commanding descent."""

    import torch

    state = learning_lab._runtime_task_state(env)
    action = torch.zeros((env.num_envs, 3), device=env.device)
    settled = env.episode_length_buf >= 20
    action[:, :2] = torch.clamp(
        -state["peg_pos_rel_hole"][:, :2] / learning_lab.ACTION_SCALE_M * 1.00,
        -1.0,
        1.0,
    )
    action[:, 2] = torch.where(
        settled & (state["insertion_depth"] < learning_lab.SUCCESS_DEPTH_M),
        torch.full_like(state["insertion_depth"], -0.45),
        torch.zeros_like(state["insertion_depth"]),
    )
    action = torch.where(settled.unsqueeze(-1), action, torch.zeros_like(action))
    return action


def policy_observation_tensor(observations: Any) -> Any:
    """Return the policy tensor from either a TensorDict or raw tensor."""

    try:
        return observations["policy"]
    except (KeyError, IndexError, TypeError):
        pass
    return observations


def install_paired_reset(
    num_envs: int,
    learning_lab: Any,
    registration: Any,
    plan: list[list[dict[str, Any]]],
    episodes_per_env: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Inject the fixed plan while leaving the canonical task implementation intact."""

    import torch

    cursor = [0] * num_envs
    episode_inputs: list[dict[str, Any] | None] = [None] * num_envs
    consumed = [False] * num_envs
    state = {"enabled": False}
    original_reset = learning_lab.reset_peg_insert

    def paired_reset_peg_insert(task_env: Any, env_ids: Any) -> None:
        if not state["enabled"]:
            original_reset(task_env, env_ids)
            return
        learning_lab.reset_scene_to_default(task_env, env_ids)
        ids = learning_lab._env_ids(task_env, env_ids)
        for env_id in ids.detach().cpu().tolist():
            consumed[int(env_id)] = False
        active_pairs = [
            (int(env_id), cursor[int(env_id)])
            for env_id in ids.detach().cpu().tolist()
            if cursor[int(env_id)] < episodes_per_env
        ]
        if not active_pairs:
            return
        active_ids = torch.as_tensor(
            [env_id for env_id, _ in active_pairs], device=task_env.device, dtype=torch.long
        )
        entries = [plan[env_id][episode_index] for env_id, episode_index in active_pairs]
        hole_offsets = torch.as_tensor(
            [[entry["hole_offset_x_mm"] / 1000.0, entry["hole_offset_y_mm"] / 1000.0] for entry in entries],
            device=task_env.device,
            dtype=torch.float32,
        )
        peg_offsets = torch.as_tensor(
            [
                [
                    entry["peg_initial_offset_x_mm"] / 1000.0,
                    entry["peg_initial_offset_y_mm"] / 1000.0,
                ]
                for entry in entries
            ],
            device=task_env.device,
            dtype=torch.float32,
        )
        task_env._hole_offset_xy[active_ids] = hole_offsets
        plate_center = torch.as_tensor(registration.PLATE_CENTER_POS, device=task_env.device)
        hole_center_w = task_env.scene.env_origins[active_ids] + plate_center
        hole_center_w[:, :2] += hole_offsets
        task_env._hole_center_w[active_ids] = hole_center_w
        learning_lab._move_socket(task_env, active_ids, hole_center_w)
        task_env.sim.forward()
        task_env.scene.update(dt=task_env.physics_dt)

        robot = task_env.scene["robot"]
        default_pos = robot.data.default_joint_pos.torch[active_ids].clone()
        default_vel = robot.data.default_joint_vel.torch[active_ids].clone()
        target_pos = hole_center_w.clone()
        target_pos[:, 2] += learning_lab.HOLE_TOP_Z + learning_lab.APPROACH_HEIGHT_M
        target_pos[:, :2] += peg_offsets
        action_term = task_env.action_manager.get_term("arm_action")
        joint_pos = default_pos
        damping = (0.02**2) * torch.eye(6, device=task_env.device).expand(len(active_ids), -1, -1)
        for _ in range(8):
            robot.write_joint_position_to_sim_index(position=joint_pos, env_ids=active_ids)
            robot.write_joint_velocity_to_sim_index(velocity=default_vel, env_ids=active_ids)
            task_env.sim.forward()
            task_env.scene.update(dt=task_env.physics_dt)
            error = target_pos - learning_lab._runtime_task_state(task_env)["peg_tip_pos_w"][active_ids]
            desired_delta = torch.zeros((len(active_ids), 6), device=task_env.device)
            desired_delta[:, :3] = torch.clamp(error, min=-0.08, max=0.08)
            jacobian = action_term._compute_frame_jacobian()[active_ids]
            dq = jacobian.transpose(1, 2) @ torch.linalg.solve(
                jacobian @ jacobian.transpose(1, 2) + damping, desired_delta.unsqueeze(-1)
            )
            joint_pos = joint_pos + dq.squeeze(-1)
            if hasattr(robot.data, "soft_joint_pos_limits"):
                limits = robot.data.soft_joint_pos_limits.torch[active_ids]
                joint_pos = torch.clamp(joint_pos, limits[..., 0], limits[..., 1])
        if hasattr(robot.data, "soft_joint_pos_limits"):
            limits = robot.data.soft_joint_pos_limits.torch[active_ids]
            joint_pos = torch.clamp(joint_pos, limits[..., 0], limits[..., 1])
        robot.write_joint_position_to_sim_index(position=joint_pos, env_ids=active_ids)
        robot.write_joint_velocity_to_sim_index(velocity=default_vel, env_ids=active_ids)
        robot.set_joint_position_target_index(target=joint_pos, env_ids=active_ids)
        for (env_id, _), entry in zip(active_pairs, entries, strict=True):
            episode_inputs[env_id] = entry
            cursor[env_id] += 1
            consumed[env_id] = True

    learning_lab.reset_peg_insert = paired_reset_peg_insert
    return {"cursor": cursor, "episode_inputs": episode_inputs, "consumed": consumed}, state


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "episodes": 0,
            "timeouts": 0,
            "mean_final_xy_error_mm": None,
            "median_final_xy_error_mm": None,
            "mean_max_insertion_depth_mm": None,
            "median_max_insertion_depth_mm": None,
            "mean_max_contact_force_n": None,
            "median_max_contact_force_n": None,
        }
    return {
        "episodes": len(records),
        "timeouts": sum(bool(record["timeout"]) for record in records),
        "mean_final_xy_error_mm": statistics.mean(record["final_xy_error_m"] * 1000.0 for record in records),
        "median_final_xy_error_mm": statistics.median(
            record["final_xy_error_m"] * 1000.0 for record in records
        ),
        "mean_max_insertion_depth_mm": statistics.mean(
            record["max_insertion_depth_m"] * 1000.0 for record in records
        ),
        "median_max_insertion_depth_mm": statistics.median(
            record["max_insertion_depth_m"] * 1000.0 for record in records
        ),
        "mean_max_contact_force_n": statistics.mean(record["max_contact_force_n"] for record in records),
        "median_max_contact_force_n": statistics.median(record["max_contact_force_n"] for record in records),
    }


try:
    import gymnasium as gym
    import torch
    from isaaclab.utils.seed import configure_seed
    from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper, handle_deprecated_rsl_rl_cfg
    from isaaclab_tasks.utils import parse_env_cfg
    from rsl_rl.runners import OnPolicyRunner

    registration = importlib.import_module(
        "experiments.robot.020_ur10e_peg_in_hole_state_precision.registration"
    )
    registration.register_tasks()
    learning_lab = importlib.import_module("experiments.robot.018_ur10e_peg_in_hole.learning_lab")
    device = args.device or "cuda:0"
    paired_mode = args.mode == "paired"
    if paired_mode:
        if args.num_envs != 64 or args.episodes_per_env != 4 or args.episodes != 256:
            raise ValueError(
                "Paired mode requires 64 environments, four episodes per environment, and 256 episodes."
            )
        if args.seed != args.paired_reset_seed:
            raise ValueError("Paired mode requires --seed equal to --paired-reset-seed.")
        plan_document, plan_sha256 = build_reset_plan(
            args.paired_reset_seed, args.num_envs, args.episodes_per_env
        )
        if plan_sha256 != PAIRED_PLAN_SHA256:
            raise RuntimeError(f"Unexpected paired plan SHA-256: {plan_sha256}")
    else:
        plan_document, plan_sha256 = None, None

    paired_state: dict[str, Any] | None = None
    paired_control: dict[str, Any] | None = None
    oracle_control: dict[str, Any] | None = None
    if args.mode == "oracle":
        nominal_plan = [
            [
                {
                    "env_id": env_id,
                    "episode_index": 0,
                    "hole_offset_x_mm": 0.0,
                    "hole_offset_y_mm": 0.0,
                    "peg_initial_offset_x_mm": 0.0,
                    "peg_initial_offset_y_mm": 0.0,
                }
            ]
            for env_id in range(args.num_envs)
        ]
        _, oracle_control = install_paired_reset(
            args.num_envs,
            learning_lab,
            registration,
            nominal_plan,
            1,
        )
    if paired_mode:
        assert plan_document is not None
        paired_state, paired_control = install_paired_reset(
            args.num_envs,
            learning_lab,
            registration,
            plan_document["plan"],
            args.episodes_per_env,
        )

    env_cfg = parse_env_cfg(args.task, device=device, num_envs=args.num_envs)
    env_cfg.env_name = args.task
    env_cfg.seed = args.seed
    env_cfg.sim.device = device
    env_cfg.scene.num_envs = args.num_envs
    base_env = gym.make(args.task, cfg=env_cfg).unwrapped
    agent_cfg = registration.UR10eStatePrecisionPPORunnerCfg()
    agent_cfg.seed = args.seed
    agent_cfg.device = device
    agent_cfg = handle_deprecated_rsl_rl_cfg(agent_cfg, metadata.version("rsl-rl-lib"))
    vec_env = RslRlVecEnvWrapper(base_env, clip_actions=agent_cfg.clip_actions)
    if paired_control is not None:
        paired_control["enabled"] = True
    if oracle_control is not None:
        oracle_control["enabled"] = True

    checkpoint_sha = None
    policy = None
    if args.mode in {"paired", "holdout"}:
        if args.checkpoint is None or not args.checkpoint.is_file():
            raise FileNotFoundError("--checkpoint is required for paired and holdout evaluation.")
        checkpoint_sha = checkpoint_sha256(args.checkpoint)
        runner = OnPolicyRunner(vec_env, agent_cfg.to_dict(), log_dir=None, device=device)
        runner.load(str(args.checkpoint))
        policy = runner.get_inference_policy(device=base_env.device)
    configure_seed(args.seed, True)

    observation_space_text = str(base_env.observation_space)
    action_space_text = str(base_env.action_space)
    initial_observations = vec_env.get_observations()
    policy_observation_shape = list(policy_observation_tensor(initial_observations).shape)
    action_dimension = int(base_env.action_manager.total_action_dim)

    if args.mode == "runtime":
        observations = initial_observations
        start = time.perf_counter()
        steps_run = 0
        for step in range(args.steps):
            action = torch.zeros((args.num_envs, action_dimension), device=base_env.device)
            with torch.inference_mode():
                observations, _, _, _ = vec_env.step(action)
            steps_run = step + 1
            if not simulation_app.is_running():
                break
        elapsed_s = time.perf_counter() - start
        summary = {
            "experiment": "020",
            "mode": args.mode,
            "task": args.task,
            "seed": args.seed,
            "num_envs": args.num_envs,
            "steps_requested": args.steps,
            "steps_run": steps_run,
            "elapsed_s": elapsed_s,
            "observation_space": observation_space_text,
            "action_space": action_space_text,
            "policy_observation_shape": policy_observation_shape,
            "action_shape": [args.num_envs, action_dimension],
            "action_dimension": action_dimension,
            "finite_observations": bool(torch.isfinite(policy_observation_tensor(observations)).all().item()),
            "finite_actions": True,
        }
    else:
        episode_reward = torch.zeros(args.num_envs, device=base_env.device)
        episode_length = torch.zeros(args.num_envs, device=base_env.device, dtype=torch.long)
        episode_max_depth = torch.zeros(args.num_envs, device=base_env.device)
        episode_max_contact = torch.zeros(args.num_envs, device=base_env.device)
        records: list[dict[str, Any]] = []
        pending: list[dict[str, Any]] = []
        reset_offset_events: list[dict[str, Any]] = []
        reset_counts = [0] * args.num_envs
        paired_completed_counts = [0] * args.num_envs if paired_mode else None
        capture_enabled = False
        original_reset_idx = base_env._reset_idx
        original_step = base_env.step

        def capture_new_offsets(ids: torch.Tensor) -> None:
            offsets = base_env._hole_offset_xy[ids].detach().cpu().tolist()
            for index, env_id in enumerate(ids.detach().cpu().tolist()):
                if paired_mode:
                    assert paired_state is not None
                    if not paired_state["consumed"][env_id]:
                        continue
                reset_counts[env_id] += 1
                reset_offset_events.append(
                    {
                        "env_id": int(env_id),
                        "reset_number": reset_counts[env_id],
                        "offset_xy_mm": [round(float(value) * 1000.0, 3) for value in offsets[index]],
                    }
                )

        def capture_reset_idx(env_ids: Any) -> Any:
            ids = learning_lab._env_ids(base_env, env_ids).reshape(-1)
            if capture_enabled:
                state = learning_lab._runtime_task_state(base_env)
                success_flags = base_env.reset_terminated[ids].detach().cpu().tolist()
                timeout_flags = base_env.reset_time_outs[ids].detach().cpu().tolist()
                offsets = base_env._hole_offset_xy[ids].detach().cpu().tolist()
                final_xy = state["xy_error"][ids].detach().cpu().tolist()
                final_depth = state["insertion_depth"][ids].detach().cpu().tolist()
                max_depth = (
                    torch.maximum(episode_max_depth[ids], state["insertion_depth"][ids])
                    .detach()
                    .cpu()
                    .tolist()
                )
                max_contact = (
                    torch.maximum(episode_max_contact[ids], state["contact_force"][ids])
                    .detach()
                    .cpu()
                    .tolist()
                )
                for index, env_id in enumerate(ids.detach().cpu().tolist()):
                    episode_index = None
                    paired_entry = None
                    if paired_mode:
                        assert paired_state is not None
                        assert paired_completed_counts is not None
                        if paired_completed_counts[env_id] >= args.episodes_per_env:
                            continue
                        episode_index = paired_completed_counts[env_id]
                        paired_entry = paired_state["episode_inputs"][env_id]
                        if paired_entry is None:
                            raise RuntimeError(f"No paired reset input recorded for env {env_id}.")
                    offset = [float(value) for value in offsets[index]]
                    record: dict[str, Any] = {
                        "env_id": int(env_id),
                        "success": bool(success_flags[index]),
                        "timeout": bool(timeout_flags[index]),
                        "final_xy_error_m": float(final_xy[index]),
                        "final_insertion_depth_m": float(final_depth[index]),
                        "max_insertion_depth_m": float(max_depth[index]),
                        "max_contact_force_n": float(max_contact[index]),
                        "offset_xy_m": offset,
                        "region": region_for_offset(offset),
                    }
                    if paired_mode:
                        assert episode_index is not None
                        assert paired_entry is not None
                        record.update(
                            {
                                "episode_index": episode_index,
                                "episode_id": f"env_{env_id:02d}_ep_{episode_index:02d}",
                                "hole_plan_offset_xy_mm": [
                                    paired_entry["hole_offset_x_mm"],
                                    paired_entry["hole_offset_y_mm"],
                                ],
                                "peg_initial_offset_xy_mm": [
                                    paired_entry["peg_initial_offset_x_mm"],
                                    paired_entry["peg_initial_offset_y_mm"],
                                ],
                            }
                        )
                        paired_completed_counts[env_id] += 1
                    pending.append(record)
            result = original_reset_idx(env_ids)
            if capture_enabled:
                capture_new_offsets(ids)
            return result

        def capture_step(action: torch.Tensor) -> Any:
            pending.clear()
            result = original_step(action)
            _, reward, terminated, truncated, _ = result
            episode_reward.add_(reward.detach())
            episode_length.add_(1)
            for record in pending:
                env_id = record["env_id"]
                record["episodic_reward"] = float(episode_reward[env_id].detach().cpu().item())
                record["episode_length"] = int(episode_length[env_id].detach().cpu().item())
                records.append(record)
                episode_reward[env_id] = 0.0
                episode_length[env_id] = 0
                episode_max_depth[env_id] = 0.0
                episode_max_contact[env_id] = 0.0
            done = (terminated | truncated).to(dtype=torch.bool)
            live = ~done
            if bool(torch.any(live)):
                state = learning_lab._runtime_task_state(base_env)
                episode_max_depth[live] = torch.maximum(
                    episode_max_depth[live], state["insertion_depth"][live]
                )
                episode_max_contact[live] = torch.maximum(
                    episode_max_contact[live], state["contact_force"][live]
                )
            return result

        base_env._reset_idx = capture_reset_idx
        base_env.step = capture_step
        base_env.reset(seed=args.seed)
        initial_ids = torch.arange(args.num_envs, device=base_env.device, dtype=torch.long)
        if paired_mode:
            assert paired_state is not None
            for env_id in range(args.num_envs):
                paired_state["consumed"][env_id] = True
        capture_new_offsets(initial_ids)
        capture_enabled = True
        observations = vec_env.get_observations()
        start = time.perf_counter()
        vector_steps = 0
        while True:
            if paired_mode:
                assert paired_completed_counts is not None
                complete = all(count == args.episodes_per_env for count in paired_completed_counts)
            else:
                complete = len(records) >= args.episodes
            if complete:
                break
            if args.mode == "random":
                actions = torch.empty((args.num_envs, action_dimension), device=base_env.device).uniform_(
                    -0.3, 0.3
                )
            elif args.mode == "oracle":
                actions = deterministic_insertion_oracle(base_env, learning_lab)
            else:
                assert policy is not None
                with torch.inference_mode():
                    actions = policy(observations)
            with torch.inference_mode():
                observations, _, _, _ = vec_env.step(actions)
            vector_steps += 1
            if args.mode == "oracle" and vector_steps % 20 == 0:
                trace_state = learning_lab._runtime_task_state(base_env)
                print(
                    "[EXP020][oracle] step={} xy_mm={:.3f} depth_mm={:.3f} contact_n={:.2f}".format(
                        vector_steps,
                        float(trace_state["xy_error"][0].detach().cpu().item() * 1000.0),
                        float(trace_state["insertion_depth"][0].detach().cpu().item() * 1000.0),
                        float(trace_state["contact_force"][0].detach().cpu().item()),
                    ),
                    flush=True,
                )
            if vector_steps > 10000:
                raise RuntimeError("Evaluation exceeded 10000 vector steps before completion.")
            if args.mode == "oracle" and vector_steps >= args.steps:
                break
            if not simulation_app.is_running():
                break
        elapsed_s = time.perf_counter() - start
        if paired_mode:
            assert paired_completed_counts is not None
            if any(count != args.episodes_per_env for count in paired_completed_counts):
                raise RuntimeError(f"Paired reset counts are incomplete: {paired_completed_counts}")
            if len(records) != args.num_envs * args.episodes_per_env:
                raise RuntimeError(f"Expected 256 paired records, got {len(records)}")
            selected_records = sorted(records, key=lambda row: (row["env_id"], row["episode_index"]))
        else:
            selected_records = records[: args.episodes]
        by_region: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in selected_records:
            by_region[record["region"]].append(record)
        summary = {
            "experiment": "020",
            "mode": args.mode,
            "task": args.task,
            "checkpoint": str(args.checkpoint) if args.checkpoint else None,
            "checkpoint_sha256": checkpoint_sha,
            "seed": args.seed,
            "num_envs": args.num_envs,
            "episodes": len(selected_records),
            "successes": sum(bool(record["success"]) for record in selected_records),
            "success_rate": (
                sum(bool(record["success"]) for record in selected_records) / len(selected_records)
                if selected_records
                else 0.0
            ),
            "timeouts": sum(bool(record["timeout"]) for record in selected_records),
            "mean_final_xy_error_mm": statistics.mean(
                record["final_xy_error_m"] * 1000.0 for record in selected_records
            ),
            "median_final_xy_error_mm": statistics.median(
                record["final_xy_error_m"] * 1000.0 for record in selected_records
            ),
            "mean_max_insertion_depth_mm": statistics.mean(
                record["max_insertion_depth_m"] * 1000.0 for record in selected_records
            ),
            "median_max_insertion_depth_mm": statistics.median(
                record["max_insertion_depth_m"] * 1000.0 for record in selected_records
            ),
            "mean_episode_length": statistics.mean(record["episode_length"] for record in selected_records),
            "mean_episodic_reward": statistics.mean(record["episodic_reward"] for record in selected_records),
            "mean_max_contact_force_n": statistics.mean(
                record["max_contact_force_n"] for record in selected_records
            ),
            "median_max_contact_force_n": statistics.median(
                record["max_contact_force_n"] for record in selected_records
            ),
            "max_contact_force_n": max(record["max_contact_force_n"] for record in selected_records),
            "vector_steps": vector_steps,
            "elapsed_s": elapsed_s,
            "observation_space": observation_space_text,
            "action_space": action_space_text,
            "policy_observation_shape": policy_observation_shape,
            "action_shape": [args.num_envs, action_dimension],
            "action_dimension": action_dimension,
            "finite_observations": bool(torch.isfinite(policy_observation_tensor(observations)).all().item()),
            "regions": {
                name: {
                    "episodes": len(region_records),
                    "successes": sum(bool(record["success"]) for record in region_records),
                    "success_rate": sum(bool(record["success"]) for record in region_records)
                    / len(region_records),
                }
                for name, region_records in sorted(by_region.items())
            },
            "failure_summary": aggregate([record for record in selected_records if not record["success"]]),
            "reset_offset_events": reset_offset_events[: args.episodes],
        }
        if paired_mode:
            assert plan_sha256 is not None
            assert paired_state is not None
            summary.update(
                {
                    "paired_reset_seed": args.paired_reset_seed,
                    "episodes_per_env": args.episodes_per_env,
                    "reset_plan_dimensions": [args.num_envs, args.episodes_per_env],
                    "reset_plan_sha256": plan_sha256,
                    "paired_plan_consumed_counts": paired_state["cursor"],
                    "paired_episode_records": [
                        {
                            "episode_id": record["episode_id"],
                            "env_id": record["env_id"],
                            "episode_index": record["episode_index"],
                            "hole_offset_xy_mm": record["hole_plan_offset_xy_mm"],
                            "peg_initial_offset_xy_mm": record["peg_initial_offset_xy_mm"],
                            "success": record["success"],
                            "timeout": record["timeout"],
                            "final_xy_error_mm": record["final_xy_error_m"] * 1000.0,
                            "max_insertion_depth_mm": record["max_insertion_depth_m"] * 1000.0,
                            "episode_length": record["episode_length"],
                            "episodic_reward": record["episodic_reward"],
                            "max_wrist_contact_force_n": record["max_contact_force_n"],
                            "region": record["region"],
                        }
                        for record in selected_records
                    ],
                }
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True), flush=True)
except Exception:
    import traceback

    traceback.print_exc()
    raise SystemExit(1) from None
finally:
    if "vec_env" in locals():
        vec_env.close()
    simulation_app.close()
