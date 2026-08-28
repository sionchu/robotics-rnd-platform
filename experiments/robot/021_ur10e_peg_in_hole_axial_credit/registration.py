"""Pre-Kit-safe registration for Experiment 021's axial-credit task."""

from __future__ import annotations

import importlib
import sys
from typing import Any

import gymnasium as gym
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.utils.configclass import configclass

base = importlib.import_module("experiments.robot.020_ur10e_peg_in_hole_state_precision.registration")

TASK_ID = "Isaac-UR10e-PegInsert-AxialCredit-v1"
PLAY_TASK_ID = "Isaac-UR10e-PegInsert-AxialCredit-Play-v1"
RUNTIME_MODULE = "experiments.robot.021_ur10e_peg_in_hole_axial_credit.runtime"


def alignment_progress(env: Any):
    return base.base.alignment_progress(env)


def gated_axial_progress(env: Any):
    from . import runtime

    return runtime.gated_axial_progress(env)


def success_bonus(env: Any):
    return base.base.success_bonus(env)


@configclass
class RewardsCfg:
    """Exactly three rewards: unchanged alignment/success and axial progress."""

    alignment_progress = RewTerm(func=alignment_progress, weight=2.0)
    gated_axial_progress = RewTerm(func=gated_axial_progress, weight=3.0)
    success_bonus = RewTerm(func=success_bonus, weight=10.0)


@configclass
class UR10eAxialCreditEnvCfg(base.UR10eStatePrecisionEnvCfg):
    """Experiment 020 geometry with the single axial-credit reward change."""

    rewards: RewardsCfg = RewardsCfg()

    def __post_init__(self) -> None:
        super().__post_init__()
        self.ui_window_class_type = f"{RUNTIME_MODULE}:AxialCreditLearningLabWindow"


@configclass
class UR10eAxialCreditEnvCfg_PLAY(UR10eAxialCreditEnvCfg):
    """Single-environment configuration for the native Learning UI."""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.scene.num_envs = 1
        self.observations.policy.enable_corruption = False


@configclass
class UR10eAxialCreditPPORunnerCfg(base.UR10eStatePrecisionPPORunnerCfg):
    """The frozen Experiment 020 PPO configuration, from a fresh policy."""

    experiment_name = "ur10e_axial_credit"
    run_name = ""


def register_tasks() -> list[str]:
    """Register only the Experiment 021 train and play IDs."""

    if TASK_ID not in gym.registry:
        gym.register(
            id=TASK_ID,
            entry_point=f"{RUNTIME_MODULE}:UR10eAxialCreditEnv",
            disable_env_checker=True,
            kwargs={
                "env_cfg_entry_point": f"{__name__}:UR10eAxialCreditEnvCfg",
                "rsl_rl_cfg_entry_point": f"{__name__}:UR10eAxialCreditPPORunnerCfg",
            },
        )
    if PLAY_TASK_ID not in gym.registry:
        gym.register(
            id=PLAY_TASK_ID,
            entry_point=f"{RUNTIME_MODULE}:UR10eAxialCreditEnv",
            disable_env_checker=True,
            kwargs={
                "env_cfg_entry_point": f"{__name__}:UR10eAxialCreditEnvCfg_PLAY",
                "rsl_rl_cfg_entry_point": f"{__name__}:UR10eAxialCreditPPORunnerCfg",
            },
        )
    return list(sys.argv[1:])
