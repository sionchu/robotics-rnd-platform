"""Finite semantic probe for the Experiment 021 axial-credit reward."""

from __future__ import annotations

import argparse
import importlib
import json
import time
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Experiment 021 reward-credit semantic probe")
parser.add_argument("--task", default="Isaac-UR10e-PegInsert-AxialCredit-Play-v1")
parser.add_argument("--steps", type=int, default=220)
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
    env.set_learning_mode("SEMANTIC PROBE")
    print("[EXP021] environment constructed; resetting", flush=True)
    env.reset(seed=args.seed)
    print("[EXP021] reset complete; beginning trajectory", flush=True)

    records: list[dict[str, Any]] = []
    start = time.perf_counter()
    first_positive: dict[str, Any] | None = None
    first_alignment_positive: dict[str, Any] | None = None
    first_alignment_negative: dict[str, Any] | None = None
    for step in range(args.steps):
        state_before = base_learning_lab._runtime_task_state(env)
        if step == 0:
            action = torch.zeros((1, 3), device=env.device)
            phase = "initialize"
        elif step < 24:
            action = torch.zeros((1, 3), device=env.device)
            action[:, :2] = torch.clamp(
                -state_before["peg_pos_rel_hole"][:, :2] / base_learning_lab.ACTION_SCALE_M * 0.5,
                -1.0,
                1.0,
            )
            phase = "improve"
        elif step < 36:
            action = torch.zeros((1, 3), device=env.device)
            direction = torch.sign(state_before["peg_pos_rel_hole"][:, :2])
            direction = torch.where(direction == 0.0, torch.ones_like(direction), direction)
            action[:, :2] = direction * 0.5
            phase = "worsen"
        else:
            action = torch.zeros((1, 3), device=env.device)
            action[:, :2] = torch.clamp(
                -state_before["peg_pos_rel_hole"][:, :2] / base_learning_lab.ACTION_SCALE_M * 0.5,
                -1.0,
                1.0,
            )
            aligned = state_before["xy_error"] <= base_learning_lab.ALIGNMENT_GATE_M
            action[:, 2] = torch.where(
                aligned & (state_before["insertion_depth"] < base_learning_lab.SUCCESS_DEPTH_M),
                torch.full_like(state_before["insertion_depth"], -0.45),
                torch.zeros_like(state_before["insertion_depth"]),
            )
            phase = "descend"
        with torch.inference_mode():
            _, _, terminated, truncated, _ = env.step(action)
        ui_after = env.task_state_for_ui()
        reward_terms = ui_after["reward_terms"]
        axial_remaining_mm = max(
            ui_after["z_error_mm"] + base_learning_lab.SUCCESS_DEPTH_M * 1000.0,
            0.0,
        )
        record = {
            "step": step + 1,
            "xy_error_mm": ui_after["xy_error_mm"],
            "peg_z_mm": ui_after["peg_z_mm"],
            "z_error_mm": ui_after["z_error_mm"],
            "axial_remaining_mm": axial_remaining_mm,
            "insertion_depth_mm": ui_after["insertion_mm"],
            "alignment_reward": reward_terms.get("alignment_progress", 0.0),
            "axial_reward": reward_terms.get("gated_axial_progress", 0.0),
            "success_reward": reward_terms.get("success_bonus", 0.0),
            "phase": phase,
            "inside_xy_gate": ui_after["xy_error_mm"] <= base_learning_lab.ALIGNMENT_GATE_M * 1000.0,
            "above_hole_top": ui_after["z_error_mm"] > 0.0,
            "terminated": bool(torch.any(terminated).detach().cpu().item()),
            "truncated": bool(torch.any(truncated).detach().cpu().item()),
            "action": [float(value) for value in action[0].detach().cpu().tolist()],
        }
        records.append(record)
        if first_alignment_positive is None and phase == "improve" and record["alignment_reward"] > 1.0e-9:
            first_alignment_positive = record.copy()
        if first_alignment_negative is None and phase == "worsen" and record["alignment_reward"] < -1.0e-9:
            first_alignment_negative = record.copy()
        if (
            first_positive is None
            and record["above_hole_top"]
            and record["inside_xy_gate"]
            and record["insertion_depth_mm"] <= 1.0e-6
            and record["axial_reward"] > 1.0e-9
        ):
            first_positive = record.copy()
        if bool(torch.any(terminated | truncated).detach().cpu().item()):
            break

    elapsed_s = time.perf_counter() - start
    summary = {
        "experiment": "021",
        "mode": "semantic_probe",
        "task": args.task,
        "seed": args.seed,
        "steps_requested": args.steps,
        "steps_run": len(records),
        "elapsed_s": elapsed_s,
        "semantic_condition": {
            "alignment_positive_after_init": first_alignment_positive is not None,
            "alignment_negative_after_init": first_alignment_negative is not None,
            "above_top_insertion_zero": any(
                row["above_hole_top"] and row["insertion_depth_mm"] <= 1.0e-6 for row in records
            ),
            "above_top_axial_positive_inside_gate": first_positive is not None,
            "first_alignment_positive": first_alignment_positive,
            "first_alignment_negative": first_alignment_negative,
            "first_positive": first_positive,
        },
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary["semantic_condition"], sort_keys=True), flush=True)
    conditions = summary["semantic_condition"]
    if not all(
        conditions[key]
        for key in (
            "alignment_positive_after_init",
            "alignment_negative_after_init",
            "above_top_insertion_zero",
            "above_top_axial_positive_inside_gate",
        )
    ):
        raise RuntimeError(
            "Semantic gate failed: expected signed alignment and axial credit "
            "conditions were not all demonstrated."
        )
finally:
    if "env" in locals():
        env.close()
    simulation_app.close()
