"""Random-policy baseline with explicit axial-reward accounting."""

from __future__ import annotations

import argparse
import importlib
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Experiment 021 random baseline")
parser.add_argument("--task", default="Isaac-UR10e-PegInsert-AxialCredit-v1")
parser.add_argument("--num_envs", type=int, default=64)
parser.add_argument("--episodes", type=int, default=128)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output", type=Path, required=True)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
app_launcher = AppLauncher(vars(args))
simulation_app = app_launcher.app

try:
    import gymnasium as gym
    import torch
    from isaaclab_tasks.utils import parse_env_cfg

    registration = importlib.import_module(
        "experiments.robot.021_ur10e_peg_in_hole_axial_credit.registration"
    )
    base_learning_lab = importlib.import_module("experiments.robot.018_ur10e_peg_in_hole.learning_lab")
    registration.register_tasks()
    device = args.device or "cuda:0"
    env_cfg = parse_env_cfg(args.task, device=device, num_envs=args.num_envs)
    env_cfg.env_name = args.task
    env_cfg.seed = args.seed
    env_cfg.sim.device = device
    env_cfg.scene.num_envs = args.num_envs
    env = gym.make(args.task, cfg=env_cfg).unwrapped
    term_names = list(env.reward_manager.active_terms)
    axial_index = term_names.index("gated_axial_progress")
    env.reset(seed=args.seed)
    torch.manual_seed(args.seed)

    episode_reward = torch.zeros(args.num_envs, device=env.device)
    episode_axial_reward = torch.zeros(args.num_envs, device=env.device)
    episode_length = torch.zeros(args.num_envs, device=env.device, dtype=torch.long)
    episode_max_depth = torch.zeros(args.num_envs, device=env.device)
    records: list[dict[str, Any]] = []
    by_region: dict[str, list[dict[str, Any]]] = defaultdict(list)
    capture_enabled = False
    original_reset = env._reset_idx
    original_step = env.step

    def region_for_offset(offset_xy_m: list[float]) -> str:
        x_mm, y_mm = offset_xy_m[0] * 1000.0, offset_xy_m[1] * 1000.0
        if abs(x_mm) <= 20.0 and abs(y_mm) <= 15.0:
            return "center"
        if abs(x_mm) / 40.0 >= abs(y_mm) / 30.0:
            return "left" if x_mm < 0.0 else "right"
        return "backward" if y_mm < 0.0 else "forward"

    def reset_capture(env_ids: Any) -> Any:
        ids = base_learning_lab._env_ids(env, env_ids).reshape(-1)
        if capture_enabled:
            state = base_learning_lab._runtime_task_state(env)
            step_reward = env.reward_manager._step_reward[ids, axial_index] * env.step_dt
            total_reward = env.reward_buf[ids]
            current_depth = state["insertion_depth"][ids]
            offsets = env._hole_offset_xy[ids].detach().cpu().tolist()
            for index, env_id in enumerate(ids.detach().cpu().tolist()):
                record = {
                    "env_id": int(env_id),
                    "success": bool(env.reset_terminated[env_id].detach().cpu().item()),
                    "timeout": bool(env.reset_time_outs[env_id].detach().cpu().item()),
                    "final_xy_error_mm": float(state["xy_error"][env_id].detach().cpu().item() * 1000.0),
                    "max_insertion_depth_mm": float(
                        torch.maximum(episode_max_depth[env_id], current_depth[index]).detach().cpu().item()
                        * 1000.0
                    ),
                    "episode_length": int(episode_length[env_id].detach().cpu().item() + 1),
                    "episodic_reward": float(
                        (episode_reward[env_id] + total_reward[index]).detach().cpu().item()
                    ),
                    "axial_progress_reward": float(
                        (episode_axial_reward[env_id] + step_reward[index]).detach().cpu().item()
                    ),
                    "offset_xy_m": [float(value) for value in offsets[index]],
                }
                record["region"] = region_for_offset(record["offset_xy_m"])
                records.append(record)
                by_region[record["region"]].append(record)
        result = original_reset(env_ids)
        if capture_enabled:
            episode_reward[ids] = 0.0
            episode_axial_reward[ids] = 0.0
            episode_length[ids] = 0
            episode_max_depth[ids] = 0.0
        return result

    def step_capture(action: torch.Tensor) -> Any:
        result = original_step(action)
        _, reward, terminated, truncated, _ = result
        done = terminated | truncated
        live = ~done
        if bool(torch.any(live)):
            episode_reward[live] += reward[live]
            episode_axial_reward[live] += env.reward_manager._step_reward[live, axial_index] * env.step_dt
            episode_length[live] += 1
            state = base_learning_lab._runtime_task_state(env)
            episode_max_depth[live] = torch.maximum(episode_max_depth[live], state["insertion_depth"][live])
        return result

    env._reset_idx = reset_capture
    env.step = step_capture
    observations, _ = env.reset(seed=args.seed)
    capture_enabled = True
    start = time.perf_counter()
    vector_steps = 0
    while len(records) < args.episodes:
        actions = torch.empty(
            (args.num_envs, env.action_manager.total_action_dim), device=env.device
        ).uniform_(-0.3, 0.3)
        observations, _, _, _, _ = env.step(actions)
        vector_steps += 1
        if vector_steps > 10000:
            raise RuntimeError("Random baseline exceeded 10000 vector steps.")
        if not simulation_app.is_running():
            break
    selected = records[: args.episodes]
    summary = {
        "experiment": "021",
        "mode": "random",
        "task": args.task,
        "seed": args.seed,
        "num_envs": args.num_envs,
        "episodes": len(selected),
        "successes": sum(bool(row["success"]) for row in selected),
        "success_rate": sum(bool(row["success"]) for row in selected) / len(selected),
        "timeouts": sum(bool(row["timeout"]) for row in selected),
        "mean_final_xy_error_mm": statistics.mean(row["final_xy_error_mm"] for row in selected),
        "median_final_xy_error_mm": statistics.median(row["final_xy_error_mm"] for row in selected),
        "mean_max_insertion_depth_mm": statistics.mean(row["max_insertion_depth_mm"] for row in selected),
        "mean_episode_length": statistics.mean(row["episode_length"] for row in selected),
        "mean_episodic_reward": statistics.mean(row["episodic_reward"] for row in selected),
        "mean_axial_progress_reward": statistics.mean(row["axial_progress_reward"] for row in selected),
        "median_axial_progress_reward": statistics.median(row["axial_progress_reward"] for row in selected),
        "vector_steps": vector_steps,
        "elapsed_s": time.perf_counter() - start,
        "reward_terms": term_names,
        "observation_space": str(env.observation_space),
        "action_space": str(env.action_space),
        "policy_observation_shape": [args.num_envs, int(env.observation_manager.group_obs_dim["policy"][0])],
        "action_dimension": int(env.action_manager.total_action_dim),
        "regions": {
            region: {
                "episodes": len(rows),
                "successes": sum(bool(row["success"]) for row in rows),
                "success_rate": sum(bool(row["success"]) for row in rows) / len(rows),
            }
            for region, rows in sorted(by_region.items())
        },
        "records": selected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps({key: summary[key] for key in ("episodes", "successes", "mean_axial_progress_reward")}),
        flush=True,
    )
finally:
    if "env" in locals():
        env.close()
    simulation_app.close()
