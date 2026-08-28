"""Experiment 019 visual comparison for the frozen Experiment 018 policy."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata as metadata
import json
import time
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher

EXPECTED_CHECKPOINT_SHA256 = "D5D9AED8CA05D6BF5A9E64357BE146DD8E10782646ADEDC3E255A962CCF7CFAF"
PEG_SIDE_MM = 40.0
BASE_SUCCESS_TOLERANCE_MM = 5.0


parser = argparse.ArgumentParser(description="Experiment 019 precision GUI playback")
parser.add_argument("--task", default="Isaac-UR10e-PegInsert-Learning-Play-v1")
parser.add_argument("--checkpoint", type=Path, required=True)
parser.add_argument("--hole_mm", type=float, required=True, choices=(50.0, 48.0, 46.0, 44.0))
parser.add_argument("--steps", type=int, default=240)
parser.add_argument("--seed", type=int, default=43)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--video_folder", type=Path, required=True)
parser.add_argument("--video_length", type=int, default=240)
parser.add_argument("--video", action="store_true")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if args.video:
    args.enable_cameras = True
app_launcher = AppLauncher(vars(args))
simulation_app = app_launcher.app


def checkpoint_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def patch_geometry(env_cfg: Any, registration: Any, hole_side_m: float) -> float:
    wall_thickness = float(registration.WALL_THICKNESS)
    hole_depth = float(registration.HOLE_DEPTH)
    wall_offset = hole_side_m / 2.0 + wall_thickness / 2.0
    wall_z = float(registration.HOLE_BOTTOM_Z) + hole_depth / 2.0
    plate_x, plate_y, _ = registration.PLATE_CENTER_POS
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
    return (hole_side_m - registration.PEG_WIDTH) / 2.0


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
    actual_sha256 = checkpoint_sha256(args.checkpoint)
    if actual_sha256 != EXPECTED_CHECKPOINT_SHA256:
        raise RuntimeError(f"Checkpoint SHA-256 mismatch: {actual_sha256}")

    device = args.device or "cuda:0"
    hole_side_m = args.hole_mm / 1000.0
    clearance_m = (hole_side_m - registration.PEG_WIDTH) / 2.0
    success_lateral_m = min(BASE_SUCCESS_TOLERANCE_MM / 1000.0, clearance_m)
    registration.HOLE_INNER = hole_side_m
    learning_lab.HOLE_INNER = hole_side_m
    registration.SUCCESS_LATERAL_M = success_lateral_m
    learning_lab.SUCCESS_LATERAL_M = success_lateral_m

    def precision_success_termination(env: Any) -> torch.Tensor:
        state = learning_lab._runtime_task_state(env)
        return (state["xy_error"] <= success_lateral_m) & (
            state["insertion_depth"] >= learning_lab.SUCCESS_DEPTH_M
        )

    learning_lab.success_termination = precision_success_termination

    env_cfg = parse_env_cfg(args.task, device=device, num_envs=1)
    env_cfg.env_name = args.task
    env_cfg.seed = args.seed
    env_cfg.sim.device = device
    env_cfg.scene.num_envs = 1
    patch_geometry(env_cfg, registration, hole_side_m)
    raw_env = gym.make(args.task, cfg=env_cfg, render_mode="rgb_array" if args.video else None)
    base_env = raw_env.unwrapped
    base_env.set_learning_mode("TRAINED PPO")

    import omni.ui

    precision_window = omni.ui.Window("Experiment 019 Precision", width=250, height=100)
    with precision_window.frame, omni.ui.VStack(spacing=4):
        omni.ui.Label(f"Hole: {args.hole_mm:.0f} mm")
        omni.ui.Label(f"Clearance: {clearance_m * 1000.0:.1f} mm")
        omni.ui.Label("Frozen PPO | seed 43 | TRAINED PPO")

    if args.video:
        args.video_folder.mkdir(parents=True, exist_ok=True)
        raw_env = gym.wrappers.RecordVideo(
            raw_env,
            video_folder=str(args.video_folder),
            step_trigger=lambda step: step == 0,
            video_length=args.video_length,
            disable_logger=True,
        )

    agent_cfg = registration.UR10ePegInsertPPORunnerCfg()
    agent_cfg.seed = args.seed
    agent_cfg.device = device
    agent_cfg = handle_deprecated_rsl_rl_cfg(agent_cfg, metadata.version("rsl-rl-lib"))
    env = RslRlVecEnvWrapper(raw_env, clip_actions=agent_cfg.clip_actions)
    runner = OnPolicyRunner(env, agent_cfg.to_dict(), log_dir=None, device=device)
    runner.load(str(args.checkpoint))
    policy = runner.get_inference_policy(device=env.unwrapped.device)
    configure_seed(args.seed, True)

    reset_offsets: list[list[float]] = []
    original_reset_idx = env.unwrapped._reset_idx

    def capture_reset_idx(env_ids: Any) -> Any:
        result = original_reset_idx(env_ids)
        ids = torch.as_tensor(env_ids, device=env.unwrapped.device, dtype=torch.long).reshape(-1)
        offsets = env.unwrapped._hole_offset_xy[ids].detach().cpu().tolist()
        reset_offsets.extend([[round(float(value) * 1000.0, 3) for value in pair] for pair in offsets])
        return result

    env.unwrapped._reset_idx = capture_reset_idx
    observations = env.get_observations()
    start = time.perf_counter()
    steps_run = 0
    for step in range(args.steps):
        with torch.inference_mode():
            actions = policy(observations)
            observations, _, _, _ = env.step(actions)
        steps_run = step + 1
        if not simulation_app.is_running():
            break
    elapsed_s = time.perf_counter() - start
    summary = {
        "experiment": "019",
        "task": args.task,
        "hole_side_mm": args.hole_mm,
        "peg_side_mm": PEG_SIDE_MM,
        "side_clearance_mm": clearance_m * 1000.0,
        "success_lateral_tolerance_mm": success_lateral_m * 1000.0,
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": actual_sha256,
        "seed": args.seed,
        "steps": args.steps,
        "actual_steps": steps_run,
        "elapsed_s": elapsed_s,
        "mode": env.unwrapped.learning_mode,
        "reset_offsets_mm": reset_offsets,
        "video_folder": str(args.video_folder),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True), flush=True)
finally:
    if "env" in locals():
        env.close()
    if "precision_window" in locals():
        precision_window.destroy()
    simulation_app.close()
