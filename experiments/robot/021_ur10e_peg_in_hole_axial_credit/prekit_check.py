"""Verify the Experiment 021 task and its single reward-topology change."""

from __future__ import annotations

import importlib
import json


def main() -> int:
    registration = importlib.import_module(
        "experiments.robot.021_ur10e_peg_in_hole_axial_credit.registration"
    )
    registration.register_tasks()
    env_cfg = registration.UR10eAxialCreditEnvCfg()
    play_cfg = registration.UR10eAxialCreditEnvCfg_PLAY()
    ppo_cfg = registration.UR10eAxialCreditPPORunnerCfg()
    env_cfg.validate()
    play_cfg.validate()

    rewards = env_cfg.rewards
    reward_names = [
        name
        for name in ("alignment_progress", "gated_axial_progress", "success_bonus")
        if hasattr(rewards, name)
    ]
    policy = env_cfg.observations.policy
    observation_terms = [
        name
        for name in ("peg_pos_rel_hole", "peg_linear_velocity", "previous_action", "insertion_depth")
        if hasattr(policy, name)
    ]
    action_cfg = env_cfg.actions.arm_action
    report = {
        "task_id": registration.TASK_ID,
        "play_task_id": registration.PLAY_TASK_ID,
        "train_envs": env_cfg.scene.num_envs,
        "play_envs": play_cfg.scene.num_envs,
        "hole_inner_mm": registration.base.HOLE_INNER * 1000.0,
        "success_lateral_mm": registration.base.SUCCESS_LATERAL_M * 1000.0,
        "success_depth_mm": registration.base.SUCCESS_DEPTH_M * 1000.0,
        "observation_terms": observation_terms,
        "action_dimension": 3,
        "action_scale_m": action_cfg.scale,
        "action_type": action_cfg.controller.command_type,
        "ik_method": action_cfg.controller.ik_method,
        "ik_lambda": action_cfg.controller.ik_params["lambda_val"],
        "reward_names": reward_names,
        "reward_weights": {name: getattr(rewards, name).weight for name in reward_names},
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
    checks = {
        "task_registered": registration.TASK_ID,
        "play_registered": registration.PLAY_TASK_ID,
        "hole_46_mm": report["hole_inner_mm"] == 46.0,
        "success_3_mm": report["success_lateral_mm"] == 3.0,
        "train_64_envs": report["train_envs"] == 64,
        "play_1_env": report["play_envs"] == 1,
        "ten_observation_values": len(report["observation_terms"]) == 4,
        "three_action_values": report["action_dimension"] == 3,
        "dls_lambda_002": report["ik_lambda"] == 0.02,
        "three_reward_terms": reward_names == ["alignment_progress", "gated_axial_progress", "success_bonus"],
        "no_old_insertion_term": not hasattr(rewards, "insertion_progress"),
        "axial_weight_3": report["reward_weights"].get("gated_axial_progress") == 3.0,
        "ppo_1000": report["ppo"]["max_iterations"] == 1000,
        "ppo_24_steps": report["ppo"]["num_steps_per_env"] == 24,
    }
    report["acceptance"] = checks
    print(json.dumps(report, indent=2, sort_keys=True))
    if not all(checks.values()):
        raise SystemExit("Experiment 021 pre-Kit acceptance failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
