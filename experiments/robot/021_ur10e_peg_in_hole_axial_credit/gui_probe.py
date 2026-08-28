"""Single-environment GUI probe for Experiment 021's axial-credit UI."""

from __future__ import annotations

import argparse
import importlib
import json
import time
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Experiment 021 GUI probe")
parser.add_argument("--task", default="Isaac-UR10e-PegInsert-AxialCredit-Play-v1")
parser.add_argument("--steps", type=int, default=180)
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
    runtime = importlib.import_module("experiments.robot.021_ur10e_peg_in_hole_axial_credit.runtime")
    base_learning_lab = importlib.import_module("experiments.robot.018_ur10e_peg_in_hole.learning_lab")
    registration.register_tasks()
    device = args.device or "cuda:0"
    env_cfg = parse_env_cfg(args.task, device=device, num_envs=1)
    env_cfg.env_name = args.task
    env_cfg.seed = args.seed
    env_cfg.sim.device = device
    env_cfg.scene.num_envs = 1
    env = gym.make(args.task, cfg=env_cfg).unwrapped
    env.set_learning_mode("AXIAL CREDIT GUI")
    env.reset(seed=args.seed)
    start = time.perf_counter()
    samples: list[dict[str, float | int | str]] = []
    successes = 0
    timeouts = 0
    for step in range(args.steps):
        state = base_learning_lab._runtime_task_state(env)
        action = torch.zeros((1, 3), device=env.device)
        action[:, :2] = torch.clamp(
            -state["peg_pos_rel_hole"][:, :2] / base_learning_lab.ACTION_SCALE_M * 0.70,
            -1.0,
            1.0,
        )
        inside_gate = state["xy_error"] <= base_learning_lab.ALIGNMENT_GATE_M
        target_reached = runtime.axial_remaining(env) <= 1.0e-6
        action[:, 2] = torch.where(
            inside_gate & ~target_reached,
            torch.full((1,), -0.45, device=env.device),
            torch.zeros((1,), device=env.device),
        )
        with torch.inference_mode():
            _, _, terminated, truncated, _ = env.step(action)
        ui_state = env.task_state_for_ui()
        rewards = ui_state["reward_terms"]
        samples.append(
            {
                "step": step + 1,
                "xy_error_mm": ui_state["xy_error_mm"],
                "axial_remaining_mm": ui_state["axial_remaining_mm"],
                "insertion_depth_mm": ui_state["insertion_mm"],
                "axial_progress_reward": rewards.get("gated_axial_progress", 0.0),
                "success": ui_state["success"],
            }
        )
        successes += int(terminated[0].detach().cpu().item())
        timeouts += int(truncated[0].detach().cpu().item())
        if bool(terminated[0].item() or truncated[0].item()) or not simulation_app.is_running():
            break
    summary = {
        "experiment": "021",
        "task": args.task,
        "seed": args.seed,
        "steps_requested": args.steps,
        "steps_run": len(samples),
        "elapsed_s": time.perf_counter() - start,
        "successes_seen": successes,
        "timeouts_seen": timeouts,
        "observation_space": str(env.observation_space),
        "action_space": str(env.action_space),
        "ui_labels": {
            "flow": "ALIGN  ↓  AXIAL APPROACH  ↓  INSERT  ↓  SUCCESS",
            "remaining": "Axial Remaining: xx.x mm",
            "reward": "Axial Progress Reward: +x.xxxx",
        },
        "samples": samples,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True), flush=True)
finally:
    if "env" in locals():
        env.close()
    simulation_app.close()
