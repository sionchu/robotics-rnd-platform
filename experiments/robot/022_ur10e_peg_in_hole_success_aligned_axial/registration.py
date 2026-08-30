"""Pre-Kit-safe registration for Experiment 022's success-aligned axial task."""

from __future__ import annotations

import importlib
import sys
from typing import Any

import gymnasium as gym
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.utils.configclass import configclass

base = importlib.import_module("experiments.robot.021_ur10e_peg_in_hole_axial_credit.registration")

TASK_ID = "Isaac-UR10e-PegInsert-SuccessAlignedAxial-v1"
PLAY_TASK_ID = "Isaac-UR10e-PegInsert-SuccessAlignedAxial-Play-v1"
RUNTIME_MODULE = "experiments.robot.022_ur10e_peg_in_hole_success_aligned_axial.runtime"

# The axial gate is bound to the authoritative task-local precision constant.
SUCCESS_LATERAL_M = base.base.SUCCESS_LATERAL_M


def alignment_progress(env: Any):
    return base.alignment_progress(env)


def success_aligned_axial_progress(env: Any):
    from . import runtime

    return runtime.success_aligned_axial_progress(env)


def success_bonus(env: Any):
    return base.success_bonus(env)


@configclass
class RewardsCfg:
    """The Experiment 021 contract with only the axial lateral gate changed."""

    alignment_progress = RewTerm(func=alignment_progress, weight=2.0)
    success_aligned_axial_progress = RewTerm(func=success_aligned_axial_progress, weight=3.0)
    success_bonus = RewTerm(func=success_bonus, weight=10.0)


@configclass
class UR10eSuccessAlignedAxialEnvCfg(base.UR10eAxialCreditEnvCfg):
    """Experiment 021 with axial credit restricted to the 3 mm success region."""

    rewards: RewardsCfg = RewardsCfg()

    def __post_init__(self) -> None:
        super().__post_init__()
        self.ui_window_class_type = f"{RUNTIME_MODULE}:SuccessAlignedAxialLearningLabWindow"


@configclass
class UR10eSuccessAlignedAxialEnvCfg_PLAY(UR10eSuccessAlignedAxialEnvCfg):
    """Single-environment configuration for native GUI verification."""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.scene.num_envs = 1
        self.observations.policy.enable_corruption = False


@configclass
class UR10eSuccessAlignedAxialPPORunnerCfg(base.UR10eAxialCreditPPORunnerCfg):
    """The frozen Experiment 021 PPO configuration, initialized from scratch."""

    experiment_name = "ur10e_success_aligned_axial"
    run_name = ""


def register_tasks() -> list[str]:
    """Register only the Experiment 022 train and play task IDs."""

    if TASK_ID not in gym.registry:
        gym.register(
            id=TASK_ID,
            entry_point=f"{RUNTIME_MODULE}:UR10eSuccessAlignedAxialEnv",
            disable_env_checker=True,
            kwargs={
                "env_cfg_entry_point": f"{__name__}:UR10eSuccessAlignedAxialEnvCfg",
                "rsl_rl_cfg_entry_point": f"{__name__}:UR10eSuccessAlignedAxialPPORunnerCfg",
            },
        )
    if PLAY_TASK_ID not in gym.registry:
        gym.register(
            id=PLAY_TASK_ID,
            entry_point=f"{RUNTIME_MODULE}:UR10eSuccessAlignedAxialEnv",
            disable_env_checker=True,
            kwargs={
                "env_cfg_entry_point": f"{__name__}:UR10eSuccessAlignedAxialEnvCfg_PLAY",
                "rsl_rl_cfg_entry_point": f"{__name__}:UR10eSuccessAlignedAxialPPORunnerCfg",
            },
        )
    return list(sys.argv[1:])
