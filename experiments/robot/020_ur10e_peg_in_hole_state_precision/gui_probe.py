"""Single-environment visual gate for the Experiment 020 task."""

from __future__ import annotations

import argparse
import importlib
import json
import time
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Experiment 020 GUI probe")
parser.add_argument("--task", default="Isaac-UR10e-PegInsert-StatePrecision-Play-v1")
parser.add_argument("--steps", type=int, default=120)
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
        "experiments.robot.020_ur10e_peg_in_hole_state_precision.registration"
    )
    learning_lab = importlib.import_module("experiments.robot.018_ur10e_peg_in_hole.learning_lab")
    registration.register_tasks()
    device = args.device or "cuda:0"
    env_cfg = parse_env_cfg(args.task, device=device, num_envs=1)
    env_cfg.env_name = args.task
    env_cfg.seed = args.seed
    env_cfg.sim.device = device
    env_cfg.scene.num_envs = 1
    env = gym.make(args.task, cfg=env_cfg).unwrapped
    env.set_learning_mode("GUI GATE")

    import omni.ui

    window = omni.ui.Window("Experiment 020 — State-Only Precision", width=340, height=130)
    with window.frame, omni.ui.VStack(spacing=4):
        title = omni.ui.Label("EXPERIMENT 020 | STATE-ONLY PPO")
        geometry = omni.ui.Label("Hole: 46 mm | Clearance: 3 mm | Success XY: 3 mm")
        contract = omni.ui.Label("Observation: 10 state values | Action: ΔXYZ (3)")
        status = omni.ui.Label("State-only gate: starting")

    env.reset(seed=args.seed)
    start = time.perf_counter()
    steps_run = 0
    successes = 0
    timeouts = 0
    for step in range(args.steps):
        with torch.inference_mode():
            action = learning_lab._axis_probe_action(env, step)
            _, _, terminated, truncated, _ = env.step(action)
        steps_run = step + 1
        successes += int(terminated.sum().detach().cpu().item())
        timeouts += int(truncated.sum().detach().cpu().item())
        state = env.task_state_for_ui()
        status.text = (
            f"Oracle preview | XY {state['xy_error_mm']:.2f} mm | insertion "
            f"{state['insertion_mm']:.1f} mm | success {state['success']} | step {steps_run}"
        )
        if not simulation_app.is_running():
            break
    elapsed_s = time.perf_counter() - start
    summary = {
        "experiment": "020",
        "task": args.task,
        "seed": args.seed,
        "steps_requested": args.steps,
        "steps_run": steps_run,
        "elapsed_s": elapsed_s,
        "observation_space": str(env.observation_space),
        "action_space": str(env.action_space),
        "successes_seen": successes,
        "timeouts_seen": timeouts,
        "window_title": title.text,
        "geometry_label": geometry.text,
        "contract_label": contract.text,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True), flush=True)
finally:
    if "env" in locals():
        env.close()
    if "window" in locals():
        window.destroy()
    simulation_app.close()
