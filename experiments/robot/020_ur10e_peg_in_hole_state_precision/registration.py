"""Pre-Kit-safe registration for the Experiment 020 state-only task.

Experiment 020 reuses the authoritative Experiment 018 scene, manager terms,
action, observation, reward, and PPO definitions.  Only the aperture and its
geometrically consistent success tolerance are specialized here; the runtime
alias applies the same constants after Kit has started.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

import gymnasium as gym
from isaaclab.utils.configclass import configclass

base = importlib.import_module("experiments.robot.018_ur10e_peg_in_hole.registration")

TASK_ID = "Isaac-UR10e-PegInsert-StatePrecision-v1"
PLAY_TASK_ID = "Isaac-UR10e-PegInsert-StatePrecision-Play-v1"
RUNTIME_MODULE = "experiments.robot.020_ur10e_peg_in_hole_state_precision.runtime"

PEG_WIDTH = base.PEG_WIDTH
PEG_LENGTH = base.PEG_LENGTH
HOLE_INNER = 0.046
WALL_THICKNESS = base.WALL_THICKNESS
HOLE_BOTTOM_Z = base.HOLE_BOTTOM_Z
HOLE_TOP_Z = base.HOLE_TOP_Z
HOLE_DEPTH = base.HOLE_DEPTH
PLATE_CENTER_POS = base.PLATE_CENTER_POS
PLATE_SIZE = base.PLATE_SIZE
HOLE_OFFSET_X_RANGE_M = base.HOLE_OFFSET_X_RANGE_M
HOLE_OFFSET_Y_RANGE_M = base.HOLE_OFFSET_Y_RANGE_M

ACTION_SCALE_M = base.ACTION_SCALE_M
RESET_XY_OFFSET_M = base.RESET_XY_OFFSET_M
APPROACH_HEIGHT_M = base.APPROACH_HEIGHT_M
ALIGNMENT_GATE_M = base.ALIGNMENT_GATE_M
SUCCESS_LATERAL_M = 0.003
SUCCESS_DEPTH_M = base.SUCCESS_DEPTH_M

# The runtime module imports the canonical Experiment 018 implementation after
# this pre-Kit module has loaded.  These process-local values make its manager
# terms use the Experiment 020 aperture without changing either source tree.
base.HOLE_INNER = HOLE_INNER
base.SUCCESS_LATERAL_M = SUCCESS_LATERAL_M


def _configure_precision_walls(scene: Any) -> None:
    """Override only the four inherited fixture wall dimensions and poses."""

    wall_offset = HOLE_INNER / 2.0 + WALL_THICKNESS / 2.0
    wall_z = HOLE_BOTTOM_Z + HOLE_DEPTH / 2.0
    fixture_size = HOLE_INNER + 2.0 * WALL_THICKNESS
    plate_x, plate_y, _ = PLATE_CENTER_POS
    wall_x_size = (WALL_THICKNESS, fixture_size, HOLE_DEPTH)
    wall_y_size = (HOLE_INNER, WALL_THICKNESS, HOLE_DEPTH)
    scene.wall_x_neg.spawn.size = wall_x_size
    scene.wall_x_pos.spawn.size = wall_x_size
    scene.wall_y_neg.spawn.size = wall_y_size
    scene.wall_y_pos.spawn.size = wall_y_size
    scene.wall_x_neg.init_state.pos = (plate_x - wall_offset, plate_y, wall_z)
    scene.wall_x_pos.init_state.pos = (plate_x + wall_offset, plate_y, wall_z)
    scene.wall_y_neg.init_state.pos = (plate_x, plate_y - wall_offset, wall_z)
    scene.wall_y_pos.init_state.pos = (plate_x, plate_y + wall_offset, wall_z)


@configclass
class UR10eStatePrecisionEnvCfg(base.UR10ePegInsertEnvCfg):
    """46 mm aperture using the unchanged ten-value state contract."""

    def __post_init__(self) -> None:
        super().__post_init__()
        _configure_precision_walls(self.scene)
        self.ui_window_class_type = f"{RUNTIME_MODULE}:LearningLabWindow"


@configclass
class UR10eStatePrecisionEnvCfg_PLAY(UR10eStatePrecisionEnvCfg):
    """Single-environment visual configuration."""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.scene.num_envs = 1
        self.observations.policy.enable_corruption = False


@configclass
class UR10eStatePrecisionPPORunnerCfg(base.UR10ePegInsertPPORunnerCfg):
    """Experiment 018 PPO values, trained from a fresh policy state."""

    experiment_name = "ur10e_state_precision"
    run_name = ""


def register_tasks() -> list[str]:
    """Register only the Experiment 020 train and play task IDs."""

    if TASK_ID not in gym.registry:
        gym.register(
            id=TASK_ID,
            entry_point=f"{RUNTIME_MODULE}:UR10eStatePrecisionEnv",
            disable_env_checker=True,
            kwargs={
                "env_cfg_entry_point": f"{__name__}:UR10eStatePrecisionEnvCfg",
                "rsl_rl_cfg_entry_point": f"{__name__}:UR10eStatePrecisionPPORunnerCfg",
            },
        )
    if PLAY_TASK_ID not in gym.registry:
        gym.register(
            id=PLAY_TASK_ID,
            entry_point=f"{RUNTIME_MODULE}:UR10eStatePrecisionEnv",
            disable_env_checker=True,
            kwargs={
                "env_cfg_entry_point": f"{__name__}:UR10eStatePrecisionEnvCfg_PLAY",
                "rsl_rl_cfg_entry_point": f"{__name__}:UR10eStatePrecisionPPORunnerCfg",
            },
        )
    return list(sys.argv[1:])
