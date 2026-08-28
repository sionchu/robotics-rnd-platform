"""Experiment 019: evaluate the frozen Experiment 018 policy at tighter holes.

This is an evaluation-only boundary probe.  The authoritative task, robot,
observations, actions, rewards, and PPO checkpoint remain in Experiment 018;
this module only clones the parsed environment configuration in memory,
changes the primitive hole dimensions, and applies the pre-declared geometric
success tolerance for the selected aperture.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata as metadata
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher

EXPECTED_CHECKPOINT_SHA256 = "D5D9AED8CA05D6BF5A9E64357BE146DD8E10782646ADEDC3E255A962CCF7CFAF"
SUPPORTED_HOLE_SIDES_MM = (50.0, 48.0, 46.0, 44.0)
PEG_SIDE_MM = 40.0
BASE_SUCCESS_TOLERANCE_MM = 5.0


parser = argparse.ArgumentParser(description="Experiment 019 precision boundary evaluation")
parser.add_argument("--task", default="Isaac-UR10e-PegInsert-Learning-v1")
parser.add_argument("--checkpoint", type=Path, required=True)
parser.add_argument("--hole_mm", type=float, required=True, choices=SUPPORTED_HOLE_SIDES_MM)
parser.add_argument("--num_envs", type=int, default=64)
parser.add_argument("--episodes", type=int, default=256)
parser.add_argument("--seed", type=int, default=43)
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


def region_for_offset(offset_xy_m: list[float]) -> str:
    x_mm, y_mm = offset_xy_m[0] * 1000.0, offset_xy_m[1] * 1000.0
    if abs(x_mm) <= 20.0 and abs(y_mm) <= 15.0:
        return "center"
    if abs(x_mm) / 40.0 >= abs(y_mm) / 30.0:
        return "left" if x_mm < 0.0 else "right"
    return "backward" if y_mm < 0.0 else "forward"


def configure_precision_geometry(env_cfg: Any, registration: Any, hole_side_m: float) -> dict[str, float]:
    """Patch only this parsed cfg instance with the selected primitive aperture."""

    wall_thickness = float(registration.WALL_THICKNESS)
    hole_depth = float(registration.HOLE_DEPTH)
    bottom_z = float(registration.HOLE_BOTTOM_Z)
    plate_x, plate_y, _ = registration.PLATE_CENTER_POS
    wall_offset = hole_side_m / 2.0 + wall_thickness / 2.0
    wall_z = bottom_z + hole_depth / 2.0
    fixture_size = hole_side_m + 2.0 * wall_thickness

    wall_x_size = (wall_thickness, fixture_size, hole_depth)
    wall_y_size = (hole_side_m, wall_thickness, hole_depth)
    env_cfg.scene.wall_x_neg.spawn.size = wall_x_size
    env_cfg.scene.wall_x_pos.spawn.size = wall_x_size
    env_cfg.scene.wall_y_neg.spawn.size = wall_y_size
    env_cfg.scene.wall_y_pos.spawn.size = wall_y_size
    env_cfg.scene.wall_x_neg.init_state.pos = (plate_x - wall_offset, plate_y, wall_z)
    env_cfg.scene.wall_x_pos.init_state.pos = (plate_x + wall_offset, plate_y, wall_z)
    env_cfg.scene.wall_y_neg.init_state.pos = (plate_x, plate_y - wall_offset, wall_z)
    env_cfg.scene.wall_y_pos.init_state.pos = (plate_x, plate_y + wall_offset, wall_z)

    clearance_m = (hole_side_m - registration.PEG_WIDTH) / 2.0
    # The policy uses Euclidean XY error.  L2 <= side clearance implies each
    # axis error is <= clearance, so an axis-aligned square peg cannot overlap
    # either pair of aperture walls.  Equality permits the geometric contact
    # boundary; it does not declare an over-sized peg to fit.
    success_lateral_m = min(BASE_SUCCESS_TOLERANCE_MM / 1000.0, clearance_m)
    return {
        "hole_side_m": hole_side_m,
        "side_clearance_m": clearance_m,
        "success_lateral_m": success_lateral_m,
        "hole_depth_m": hole_depth,
    }


def offset_digest(events: list[dict[str, Any]]) -> str:
    payload = json.dumps(events, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


try:
    import gymnasium as gym
    import torch
    from isaaclab.utils.seed import configure_seed
    from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper, handle_deprecated_rsl_rl_cfg
    from isaaclab_tasks.utils import parse_env_cfg
    from rsl_rl.runners import OnPolicyRunner

    registration = importlib.import_module("experiments.robot.018_ur10e_peg_in_hole.registration")
    learning_lab = importlib.import_module("experiments.robot.018_ur10e_peg_in_hole.learning_lab")
    registration.register_tasks()

    if not args.checkpoint.is_file():
        raise FileNotFoundError(f"Checkpoint does not exist: {args.checkpoint}")
    actual_checkpoint_sha256 = checkpoint_sha256(args.checkpoint)
    if actual_checkpoint_sha256 != EXPECTED_CHECKPOINT_SHA256:
        raise RuntimeError(
            "Checkpoint SHA-256 mismatch: "
            f"expected {EXPECTED_CHECKPOINT_SHA256}, got {actual_checkpoint_sha256}"
        )

    hole_side_m = args.hole_mm / 1000.0
    device = args.device or "cuda:0"
    geometry = {
        "hole_side_m": hole_side_m,
        "side_clearance_m": (hole_side_m - registration.PEG_WIDTH) / 2.0,
        "success_lateral_m": min(
            BASE_SUCCESS_TOLERANCE_MM / 1000.0,
            (hole_side_m - registration.PEG_WIDTH) / 2.0,
        ),
        "hole_depth_m": float(registration.HOLE_DEPTH),
    }

    # These are process-local bindings only.  They make the authoritative
    # Experiment 018 runtime terms use the selected geometry without editing
    # its source or changing the policy observation/action structure.
    registration.HOLE_INNER = hole_side_m
    learning_lab.HOLE_INNER = hole_side_m
    registration.SUCCESS_LATERAL_M = geometry["success_lateral_m"]
    learning_lab.SUCCESS_LATERAL_M = geometry["success_lateral_m"]

    def precision_success_termination(env: Any) -> torch.Tensor:
        state = learning_lab._runtime_task_state(env)
        return (state["xy_error"] <= geometry["success_lateral_m"]) & (
            state["insertion_depth"] >= learning_lab.SUCCESS_DEPTH_M
        )

    learning_lab.success_termination = precision_success_termination

    env_cfg = parse_env_cfg(args.task, device=device, num_envs=args.num_envs)
    env_cfg.env_name = args.task
    env_cfg.seed = args.seed
    env_cfg.sim.device = device
    env_cfg.scene.num_envs = args.num_envs
    configure_precision_geometry(env_cfg, registration, hole_side_m)
    base_env = gym.make(args.task, cfg=env_cfg).unwrapped

    agent_cfg = registration.UR10ePegInsertPPORunnerCfg()
    agent_cfg.seed = args.seed
    agent_cfg.device = device
    agent_cfg = handle_deprecated_rsl_rl_cfg(agent_cfg, metadata.version("rsl-rl-lib"))
    vec_env = RslRlVecEnvWrapper(base_env, clip_actions=agent_cfg.clip_actions)
    runner = OnPolicyRunner(vec_env, agent_cfg.to_dict(), log_dir=None, device=device)
    runner.load(str(args.checkpoint))
    policy = runner.get_inference_policy(device=base_env.device)
    configure_seed(args.seed, True)

    episode_reward = torch.zeros(args.num_envs, device=base_env.device)
    episode_length = torch.zeros(args.num_envs, device=base_env.device, dtype=torch.long)
    episode_max_depth = torch.zeros(args.num_envs, device=base_env.device)
    episode_max_contact = torch.zeros(args.num_envs, device=base_env.device)
    episode_max_misaligned_depth = torch.zeros(args.num_envs, device=base_env.device)
    episode_insertion_started_misaligned = torch.zeros(
        args.num_envs, device=base_env.device, dtype=torch.bool
    )
    records: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    reset_offset_events: list[dict[str, Any]] = []
    reset_counts = [0] * args.num_envs
    capture_enabled = False
    original_reset_idx = base_env._reset_idx
    original_step = base_env.step

    def capture_new_offsets(ids: torch.Tensor) -> None:
        offsets = base_env._hole_offset_xy[ids].detach().cpu().tolist()
        for index, env_id in enumerate(ids.detach().cpu().tolist()):
            reset_counts[env_id] += 1
            pair = [round(float(value), 9) for value in offsets[index]]
            reset_offset_events.append(
                {
                    "env_id": int(env_id),
                    "reset_number": reset_counts[env_id],
                    "offset_xy_mm": [round(value * 1000.0, 3) for value in pair],
                }
            )

    def capture_reset_idx(env_ids: Any) -> None:
        ids = torch.as_tensor(env_ids, device=base_env.device, dtype=torch.long).reshape(-1)
        if capture_enabled:
            state = learning_lab._runtime_task_state(base_env)
            success_flags = base_env.reset_terminated[ids].detach().cpu().tolist()
            timeout_flags = base_env.reset_time_outs[ids].detach().cpu().tolist()
            offsets = base_env._hole_offset_xy[ids].detach().cpu().tolist()
            final_xy = state["xy_error"][ids].detach().cpu().tolist()
            final_depth = state["insertion_depth"][ids].detach().cpu().tolist()
            max_depth = (
                torch.maximum(episode_max_depth[ids], state["insertion_depth"][ids]).detach().cpu().tolist()
            )
            max_contact = (
                torch.maximum(episode_max_contact[ids], state["contact_force"][ids]).detach().cpu().tolist()
            )
            final_misaligned_depth = torch.where(
                state["xy_error"][ids] > learning_lab.ALIGNMENT_GATE_M,
                state["insertion_depth"][ids],
                torch.zeros_like(state["insertion_depth"][ids]),
            )
            max_misaligned_depth = (
                torch.maximum(episode_max_misaligned_depth[ids], final_misaligned_depth)
                .detach()
                .cpu()
                .tolist()
            )
            insertion_started_misaligned = (
                (
                    episode_insertion_started_misaligned[ids]
                    | (
                        (final_misaligned_depth > 1.0e-5)
                        & (state["xy_error"][ids] > learning_lab.ALIGNMENT_GATE_M)
                    )
                )
                .detach()
                .cpu()
                .tolist()
            )
            for index, env_id in enumerate(ids.detach().cpu().tolist()):
                offset = [float(value) for value in offsets[index]]
                pending.append(
                    {
                        "env_id": int(env_id),
                        "success": bool(success_flags[index]),
                        "timeout": bool(timeout_flags[index]),
                        "final_xy_error_m": float(final_xy[index]),
                        "final_insertion_depth_m": float(final_depth[index]),
                        "max_insertion_depth_m": float(max_depth[index]),
                        "max_contact_force_n": float(max_contact[index]),
                        "max_misaligned_insertion_depth_m": float(max_misaligned_depth[index]),
                        "insertion_started_misaligned": bool(insertion_started_misaligned[index]),
                        "offset_xy_m": offset,
                        "region": region_for_offset(offset),
                    }
                )
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
            episode_max_misaligned_depth[env_id] = 0.0
            episode_insertion_started_misaligned[env_id] = False

        done = (terminated | truncated).to(dtype=torch.bool)
        live = ~done
        if bool(torch.any(live)):
            state = learning_lab._runtime_task_state(base_env)
            episode_max_depth[live] = torch.maximum(episode_max_depth[live], state["insertion_depth"][live])
            episode_max_contact[live] = torch.maximum(episode_max_contact[live], state["contact_force"][live])
            misaligned = state["xy_error"] > learning_lab.ALIGNMENT_GATE_M
            misaligned_depth = torch.where(
                misaligned, state["insertion_depth"], torch.zeros_like(state["insertion_depth"])
            )
            episode_max_misaligned_depth[live] = torch.maximum(
                episode_max_misaligned_depth[live], misaligned_depth[live]
            )
            episode_insertion_started_misaligned[live] |= misaligned[live] & (
                state["insertion_depth"][live] > 1.0e-5
            )
        return result

    base_env._reset_idx = capture_reset_idx
    base_env.step = capture_step
    base_env.reset(seed=args.seed)
    initial_ids = torch.arange(args.num_envs, device=base_env.device, dtype=torch.long)
    capture_new_offsets(initial_ids)
    capture_enabled = True
    observations = vec_env.get_observations()

    start = time.perf_counter()
    vector_steps = 0
    while len(records) < args.episodes:
        with torch.inference_mode():
            actions = policy(observations)
            observations, _, _, _ = vec_env.step(actions)
        vector_steps += 1
        if vector_steps % 10 == 0:
            print(
                f"[EXP019] hole_mm={args.hole_mm:.0f} vector_steps={vector_steps} records={len(records)}",
                flush=True,
            )
    elapsed_s = time.perf_counter() - start

    selected_records = records[: args.episodes]
    final_xy_mm = [record["final_xy_error_m"] * 1000.0 for record in selected_records]
    max_depth_mm = [record["max_insertion_depth_m"] * 1000.0 for record in selected_records]
    contact_force = [record["max_contact_force_n"] for record in selected_records]
    misaligned_depth = [record["max_misaligned_insertion_depth_m"] * 1000.0 for record in selected_records]
    lengths = [record["episode_length"] for record in selected_records]
    rewards = [record["episodic_reward"] for record in selected_records]
    by_region: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in selected_records:
        by_region[record["region"]].append(record)

    def aggregate(records_to_summarize: list[dict[str, Any]]) -> dict[str, Any]:
        if not records_to_summarize:
            return {
                "episodes": 0,
                "timeouts": 0,
                "mean_final_xy_error_mm": None,
                "median_final_xy_error_mm": None,
                "mean_final_insertion_depth_mm": None,
                "median_final_insertion_depth_mm": None,
                "mean_max_insertion_depth_mm": None,
                "median_max_insertion_depth_mm": None,
                "mean_max_contact_force_n": None,
                "median_max_contact_force_n": None,
                "insertion_started_misaligned_count": 0,
            }
        return {
            "episodes": len(records_to_summarize),
            "timeouts": sum(record["timeout"] for record in records_to_summarize),
            "mean_final_xy_error_mm": statistics.mean(
                record["final_xy_error_m"] * 1000.0 for record in records_to_summarize
            ),
            "median_final_xy_error_mm": statistics.median(
                record["final_xy_error_m"] * 1000.0 for record in records_to_summarize
            ),
            "mean_final_insertion_depth_mm": statistics.mean(
                record["final_insertion_depth_m"] * 1000.0 for record in records_to_summarize
            ),
            "median_final_insertion_depth_mm": statistics.median(
                record["final_insertion_depth_m"] * 1000.0 for record in records_to_summarize
            ),
            "mean_max_insertion_depth_mm": statistics.mean(
                record["max_insertion_depth_m"] * 1000.0 for record in records_to_summarize
            ),
            "median_max_insertion_depth_mm": statistics.median(
                record["max_insertion_depth_m"] * 1000.0 for record in records_to_summarize
            ),
            "mean_max_contact_force_n": statistics.mean(
                record["max_contact_force_n"] for record in records_to_summarize
            ),
            "median_max_contact_force_n": statistics.median(
                record["max_contact_force_n"] for record in records_to_summarize
            ),
            "mean_max_misaligned_insertion_depth_mm": statistics.mean(
                record["max_misaligned_insertion_depth_m"] * 1000.0 for record in records_to_summarize
            ),
            "median_max_misaligned_insertion_depth_mm": statistics.median(
                record["max_misaligned_insertion_depth_m"] * 1000.0 for record in records_to_summarize
            ),
            "insertion_started_misaligned_count": sum(
                record["insertion_started_misaligned"] for record in records_to_summarize
            ),
        }

    failed_records = [record for record in selected_records if not record["success"]]

    selected_offset_events = reset_offset_events[: args.episodes]
    summary = {
        "experiment": "019",
        "task": args.task,
        "hole_side_mm": args.hole_mm,
        "peg_side_mm": PEG_SIDE_MM,
        "side_clearance_mm": geometry["side_clearance_m"] * 1000.0,
        "success_lateral_tolerance_mm": geometry["success_lateral_m"] * 1000.0,
        "success_tolerance_rule": "min(5.0 mm, (hole_side - peg_side) / 2)",
        "insertion_depth_criterion_mm": learning_lab.SUCCESS_DEPTH_M * 1000.0,
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": actual_checkpoint_sha256,
        "seed": args.seed,
        "num_envs": args.num_envs,
        "episodes": len(selected_records),
        "successes": sum(record["success"] for record in selected_records),
        "success_rate": sum(record["success"] for record in selected_records) / len(selected_records),
        "timeouts": sum(record["timeout"] for record in selected_records),
        "mean_final_xy_error_mm": statistics.mean(final_xy_mm),
        "median_final_xy_error_mm": statistics.median(final_xy_mm),
        "mean_max_insertion_depth_mm": statistics.mean(max_depth_mm),
        "median_max_insertion_depth_mm": statistics.median(max_depth_mm),
        "mean_episode_length": statistics.mean(lengths),
        "mean_episodic_reward": statistics.mean(rewards),
        "mean_max_contact_force_n": statistics.mean(contact_force),
        "median_max_contact_force_n": statistics.median(contact_force),
        "max_contact_force_n": max(contact_force),
        "contact_positive_episode_count": sum(value > 0.0 for value in contact_force),
        "mean_max_misaligned_insertion_depth_mm": statistics.mean(misaligned_depth),
        "median_max_misaligned_insertion_depth_mm": statistics.median(misaligned_depth),
        "insertion_started_misaligned_count": sum(
            record["insertion_started_misaligned"] for record in selected_records
        ),
        "failure_summary": aggregate(failed_records),
        "vector_steps": vector_steps,
        "elapsed_s": elapsed_s,
        "regions": {
            name: {
                "episodes": len(region_records),
                "successes": sum(record["success"] for record in region_records),
                "success_rate": sum(record["success"] for record in region_records) / len(region_records),
            }
            for name, region_records in sorted(by_region.items())
        },
        "reset_offset_events": selected_offset_events,
        "reset_offset_digest": offset_digest(selected_offset_events),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True), flush=True)
finally:
    if "vec_env" in locals():
        vec_env.close()
    simulation_app.close()
