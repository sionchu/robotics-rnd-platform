"""Verify Experiment 020 registration and configuration before Kit startup."""

from __future__ import annotations

import importlib
import json


def main() -> int:
    registration = importlib.import_module(
        "experiments.robot.020_ur10e_peg_in_hole_state_precision.registration"
    )
    registered = registration.register_tasks()
    train_cfg = registration.UR10eStatePrecisionEnvCfg()
    play_cfg = registration.UR10eStatePrecisionEnvCfg_PLAY()
    ppo_cfg = registration.UR10eStatePrecisionPPORunnerCfg()
    train_cfg.validate()
    play_cfg.validate()

    action_cfg = train_cfg.actions.arm_action
    policy_cfg = train_cfg.observations.policy
    wall_cfg = train_cfg.scene.wall_x_neg
    observation_terms = [
        name
        for name in ("peg_pos_rel_hole", "peg_linear_velocity", "previous_action", "insertion_depth")
        if hasattr(policy_cfg, name)
    ]
    report = {
        "task_id": registration.TASK_ID,
        "play_task_id": registration.PLAY_TASK_ID,
        "registered_args_count": len(registered),
        "train_envs": train_cfg.scene.num_envs,
        "play_envs": play_cfg.scene.num_envs,
        "hole_inner_mm": registration.HOLE_INNER * 1000.0,
        "success_lateral_mm": registration.SUCCESS_LATERAL_M * 1000.0,
        "success_depth_mm": registration.SUCCESS_DEPTH_M * 1000.0,
        "observation_terms": observation_terms,
        "action_scale_m": action_cfg.scale,
        "action_type": action_cfg.controller.command_type,
        "ik_method": action_cfg.controller.ik_method,
        "ik_lambda": action_cfg.controller.ik_params["lambda_val"],
        "wall_x_neg_size_m": list(wall_cfg.spawn.size),
        "wall_x_neg_pos_m": list(wall_cfg.init_state.pos),
        "ppo": {
            "num_steps_per_env": ppo_cfg.num_steps_per_env,
            "max_iterations": ppo_cfg.max_iterations,
            "actor_hidden_dims": ppo_cfg.actor.hidden_dims,
            "critic_hidden_dims": ppo_cfg.critic.hidden_dims,
            "learning_rate": ppo_cfg.algorithm.learning_rate,
            "gamma": ppo_cfg.algorithm.gamma,
            "lam": ppo_cfg.algorithm.lam,
        },
    }
    required = {
        "tasks_registered": registration.TASK_ID,
        "play_registered": registration.PLAY_TASK_ID,
        "hole_46_mm": report["hole_inner_mm"] == 46.0,
        "success_3_mm": report["success_lateral_mm"] == 3.0,
        "train_64_envs": report["train_envs"] == 64,
        "play_1_env": report["play_envs"] == 1,
        "ten_observation_terms": len(report["observation_terms"]) == 4,
        "relative_position_action": report["action_type"] == "position",
        "dls_lambda_002": report["ik_lambda"] == 0.02,
        "ppo_1000": report["ppo"]["max_iterations"] == 1000,
    }
    report["acceptance"] = required
    print(json.dumps(report, indent=2, sort_keys=True))
    if not all(required.values()):
        raise SystemExit("Experiment 020 pre-Kit acceptance failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
