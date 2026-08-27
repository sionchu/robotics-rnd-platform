"""Pre-Kit-safe task registration and canonical Experiment 018 configuration.

The task implementation itself remains in ``learning_lab.py``.  This module
contains only imports that are safe before Isaac Sim's ``SimulationApp`` and
uses explicit lazy forwarders for runtime manager terms.
"""

from __future__ import annotations

import copy
import sys
from typing import Any

import gymnasium as gym
import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg, AssetBaseCfg
from isaaclab.assets.rigid_object import RigidObjectCfg
from isaaclab.controllers.differential_ik_cfg import DifferentialIKControllerCfg
from isaaclab.envs import ManagerBasedRLEnvCfg
from isaaclab.envs.mdp.actions.actions_cfg import DifferentialInverseKinematicsActionCfg
from isaaclab.managers import ActionTermCfg as ActionTerm
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import ObservationGroupCfg as ObsGroup
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import TerminationTermCfg as DoneTerm
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sensors import ContactSensorCfg
from isaaclab.sim import CollisionPropertiesCfg
from isaaclab.utils.configclass import configclass
from isaaclab_assets.robots.universal_robots import UR10e_CFG
from isaaclab_physx.physics import PhysxCfg
from isaaclab_rl.rsl_rl import RslRlMLPModelCfg, RslRlOnPolicyRunnerCfg, RslRlPpoAlgorithmCfg

TASK_ID = "Isaac-UR10e-PegInsert-Learning-v1"
PLAY_TASK_ID = "Isaac-UR10e-PegInsert-Learning-Play-v1"
RUNTIME_MODULE = "experiments.robot.018_ur10e_peg_in_hole.learning_lab"

# Geometry is deliberately primitive and dimensioned in SI units.  The XY
# location is the validated reachable fixture location from the UR10e probe.
PEG_WIDTH = 0.04
PEG_LENGTH = 0.12
HOLE_INNER = 0.05
WALL_THICKNESS = 0.02
HOLE_BOTTOM_Z = 0.02
HOLE_TOP_Z = 0.3061152
HOLE_DEPTH = HOLE_TOP_Z - HOLE_BOTTOM_Z
PLATE_CENTER_POS = (-0.6433276, -0.1740356, 0.0)
PLATE_SIZE = (0.44, 0.34, 0.04)
HOLE_OFFSET_X_RANGE_M = (-0.04, 0.04)
HOLE_OFFSET_Y_RANGE_M = (-0.03, 0.03)

ACTION_SCALE_M = 0.005
RESET_XY_OFFSET_M = 0.015
APPROACH_HEIGHT_M = 0.025
ALIGNMENT_GATE_M = 0.010
SUCCESS_LATERAL_M = 0.005
SUCCESS_DEPTH_M = 0.060


def peg_pos_rel_hole(env: Any):
    from . import learning_lab

    return learning_lab.peg_pos_rel_hole(env)


def peg_linear_velocity(env: Any):
    from . import learning_lab

    return learning_lab.peg_linear_velocity(env)


def previous_action(env: Any):
    from . import learning_lab

    return learning_lab.previous_action(env)


def insertion_depth(env: Any):
    from . import learning_lab

    return learning_lab.insertion_depth(env)


def success_termination(env: Any):
    from . import learning_lab

    return learning_lab.success_termination(env)


def timeout_termination(env: Any):
    from . import learning_lab

    return learning_lab.timeout_termination(env)


def alignment_progress(env: Any):
    from . import learning_lab

    return learning_lab.alignment_progress(env)


def insertion_progress(env: Any):
    from . import learning_lab

    return learning_lab.insertion_progress(env)


def success_bonus(env: Any):
    from . import learning_lab

    return learning_lab.success_bonus(env)


def reset_peg_insert(env: Any, env_ids: Any) -> None:
    from . import learning_lab

    return learning_lab.reset_peg_insert(env, env_ids)


def _static_box(
    prim_path: str,
    size: tuple[float, float, float],
    pos: tuple[float, float, float],
    color: tuple[float, float, float],
    *,
    collidable: bool,
) -> AssetBaseCfg:
    """Return a primitive fixture/marker using Isaac Lab's native spawner."""

    return AssetBaseCfg(
        prim_path=prim_path,
        init_state=AssetBaseCfg.InitialStateCfg(pos=pos),
        spawn=sim_utils.CuboidCfg(
            size=size,
            collision_props=CollisionPropertiesCfg() if collidable else None,
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=color, roughness=0.65),
        ),
    )


def _kinematic_box(
    prim_path: str,
    size: tuple[float, float, float],
    pos: tuple[float, float, float],
    color: tuple[float, float, float],
    *,
    collidable: bool,
) -> RigidObjectCfg:
    """Return a kinematic primitive that can be repositioned per environment."""

    return RigidObjectCfg(
        prim_path=prim_path,
        init_state=RigidObjectCfg.InitialStateCfg(pos=pos),
        spawn=sim_utils.CuboidCfg(
            size=size,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True, disable_gravity=True),
            collision_props=CollisionPropertiesCfg(collision_enabled=collidable),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=color, roughness=0.65),
        ),
    )


# Do not mutate the imported upstream configuration.  ``configclass.copy`` is
# shallow, so a deepcopy is used before enabling contact reporting for this
# external task.
UR10E_LEARNING_CFG: ArticulationCfg = copy.deepcopy(UR10e_CFG)
UR10E_LEARNING_CFG.prim_path = "{ENV_REGEX_NS}/Robot"
UR10E_LEARNING_CFG.spawn.activate_contact_sensors = True

_WALL_Z = HOLE_BOTTOM_Z + HOLE_DEPTH / 2.0
_WALL_OFFSET = HOLE_INNER / 2.0 + WALL_THICKNESS / 2.0
_FIXTURE_SIZE = HOLE_INNER + 2.0 * WALL_THICKNESS


@configclass
class SceneCfg(InteractiveSceneCfg):
    """One UR10e, a square peg, and a four-wall square-hole fixture."""

    ground = AssetBaseCfg(
        prim_path="/World/ground",
        init_state=AssetBaseCfg.InitialStateCfg(pos=(0.0, 0.0, -0.03)),
        spawn=sim_utils.GroundPlaneCfg(),
    )

    robot: ArticulationCfg = UR10E_LEARNING_CFG

    plate = _static_box(
        "{ENV_REGEX_NS}/Plate",
        PLATE_SIZE,
        PLATE_CENTER_POS,
        (0.24, 0.27, 0.32),
        collidable=True,
    )
    wall_x_neg = _kinematic_box(
        "{ENV_REGEX_NS}/Fixture/HoleWallXNeg",
        (WALL_THICKNESS, _FIXTURE_SIZE, HOLE_DEPTH),
        (PLATE_CENTER_POS[0] - _WALL_OFFSET, PLATE_CENTER_POS[1], _WALL_Z),
        (0.32, 0.36, 0.42),
        collidable=True,
    )
    wall_x_pos = _kinematic_box(
        "{ENV_REGEX_NS}/Fixture/HoleWallXPos",
        (WALL_THICKNESS, _FIXTURE_SIZE, HOLE_DEPTH),
        (PLATE_CENTER_POS[0] + _WALL_OFFSET, PLATE_CENTER_POS[1], _WALL_Z),
        (0.32, 0.36, 0.42),
        collidable=True,
    )
    wall_y_neg = _kinematic_box(
        "{ENV_REGEX_NS}/Fixture/HoleWallYNeg",
        (HOLE_INNER, WALL_THICKNESS, HOLE_DEPTH),
        (PLATE_CENTER_POS[0], PLATE_CENTER_POS[1] - _WALL_OFFSET, _WALL_Z),
        (0.32, 0.36, 0.42),
        collidable=True,
    )
    wall_y_pos = _kinematic_box(
        "{ENV_REGEX_NS}/Fixture/HoleWallYPos",
        (HOLE_INNER, WALL_THICKNESS, HOLE_DEPTH),
        (PLATE_CENTER_POS[0], PLATE_CENTER_POS[1] + _WALL_OFFSET, _WALL_Z),
        (0.32, 0.36, 0.42),
        collidable=True,
    )

    # The peg is a collision mesh attached to the terminal robot link.  It is
    # not a nested rigid body; PhysX therefore treats it as part of the arm.
    peg = AssetBaseCfg(
        prim_path="{ENV_REGEX_NS}/Robot/wrist_3_link/ProbeSquarePeg",
        init_state=AssetBaseCfg.InitialStateCfg(pos=(0.0, 0.0, PEG_LENGTH / 2.0)),
        spawn=sim_utils.CuboidCfg(
            size=(PEG_WIDTH, PEG_WIDTH, PEG_LENGTH),
            collision_props=CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.95, 0.42, 0.08), roughness=0.45),
        ),
    )
    peg_tip_marker = _static_box(
        "{ENV_REGEX_NS}/Robot/wrist_3_link/PegTipMarker",
        (0.010, 0.010, 0.010),
        (0.0, 0.0, PEG_LENGTH),
        (0.98, 0.16, 0.72),
        collidable=False,
    )

    target_marker = _kinematic_box(
        "{ENV_REGEX_NS}/Fixture/HoleTargetMarker",
        (0.012, 0.012, 0.012),
        (PLATE_CENTER_POS[0], PLATE_CENTER_POS[1], HOLE_TOP_Z + 0.006),
        (0.12, 0.86, 0.24),
        collidable=False,
    )
    insertion_axis_marker = _kinematic_box(
        "{ENV_REGEX_NS}/Fixture/InsertionAxisMarker",
        (0.006, 0.006, HOLE_DEPTH),
        (PLATE_CENTER_POS[0], PLATE_CENTER_POS[1], HOLE_BOTTOM_Z + HOLE_DEPTH / 2.0),
        (0.18, 0.56, 0.95),
        collidable=False,
    )
    light = AssetBaseCfg(
        prim_path="/World/light",
        spawn=sim_utils.DomeLightCfg(color=(0.75, 0.78, 0.84), intensity=2200.0),
    )

    wrist_contact = ContactSensorCfg(
        prim_path="{ENV_REGEX_NS}/Robot/wrist_3_link",
        update_period=0.0,
        history_length=8,
        track_air_time=False,
        track_contact_points=False,
    )


@configclass
class ActionsCfg:
    """Three-dimensional relative position commands for the peg tip."""

    arm_action: ActionTerm = DifferentialInverseKinematicsActionCfg(
        asset_name="robot",
        joint_names=["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint", "wrist_.*_joint"],
        body_name="wrist_3_link",
        body_offset=DifferentialInverseKinematicsActionCfg.OffsetCfg(pos=(0.0, 0.0, PEG_LENGTH)),
        controller=DifferentialIKControllerCfg(
            command_type="position",
            use_relative_mode=True,
            ik_method="dls",
            ik_params={"lambda_val": 0.02},
        ),
        scale=ACTION_SCALE_M,
    )


@configclass
class ObservationsCfg:
    """Exactly ten policy values: position, velocity, previous action, depth."""

    @configclass
    class PolicyCfg(ObsGroup):
        peg_pos_rel_hole = ObsTerm(func=peg_pos_rel_hole)
        peg_linear_velocity = ObsTerm(func=peg_linear_velocity)
        previous_action = ObsTerm(func=previous_action)
        insertion_depth = ObsTerm(func=insertion_depth)

        def __post_init__(self) -> None:
            self.enable_corruption = False
            self.concatenate_terms = True

    policy: PolicyCfg = PolicyCfg()


@configclass
class RewardsCfg:
    """The unchanged three conceptual rewards from v0."""

    alignment_progress = RewTerm(func=alignment_progress, weight=2.0)
    insertion_progress = RewTerm(func=insertion_progress, weight=3.0)
    success_bonus = RewTerm(func=success_bonus, weight=10.0)


@configclass
class TerminationsCfg:
    success = DoneTerm(func=success_termination)
    time_out = DoneTerm(func=timeout_termination, time_out=True)


@configclass
class EventsCfg:
    reset_peg_insert = EventTerm(func=reset_peg_insert, mode="reset")


@configclass
class UR10ePegInsertEnvCfg(ManagerBasedRLEnvCfg):
    scene: SceneCfg = SceneCfg(num_envs=64, env_spacing=2.5)
    observations: ObservationsCfg = ObservationsCfg()
    actions: ActionsCfg = ActionsCfg()
    rewards: RewardsCfg = RewardsCfg()
    terminations: TerminationsCfg = TerminationsCfg()
    events: EventsCfg = EventsCfg()
    commands: None = None
    curriculum: None = None

    def __post_init__(self) -> None:
        self.decimation = 2
        self.sim.dt = 1.0 / 60.0
        self.sim.render_interval = self.decimation
        self.sim.physics = PhysxCfg(bounce_threshold_velocity=0.2)
        self.episode_length_s = 8.0
        self.seed = 42
        self.viewer.eye = (1.25, -1.50, 1.10)
        self.viewer.lookat = (PLATE_CENTER_POS[0], PLATE_CENTER_POS[1], 0.18)
        self.ui_window_class_type = f"{RUNTIME_MODULE}:LearningLabWindow"


@configclass
class UR10ePegInsertEnvCfg_PLAY(UR10ePegInsertEnvCfg):
    def __post_init__(self) -> None:
        super().__post_init__()
        self.scene.num_envs = 1
        self.observations.policy.enable_corruption = False


@configclass
class UR10ePegInsertPPORunnerCfg(RslRlOnPolicyRunnerCfg):
    """PPO starting point copied only at the level of official Exp017 values."""

    num_steps_per_env = 24
    max_iterations = 1000
    save_interval = 50
    experiment_name = "ur10e_peg_insert_learning"
    run_name = ""
    actor = RslRlMLPModelCfg(
        hidden_dims=[64, 64],
        activation="elu",
        obs_normalization=False,
        distribution_cfg=RslRlMLPModelCfg.GaussianDistributionCfg(init_std=1.0),
    )
    critic = RslRlMLPModelCfg(hidden_dims=[64, 64], activation="elu", obs_normalization=False)
    algorithm = RslRlPpoAlgorithmCfg(
        value_loss_coef=1.0,
        use_clipped_value_loss=True,
        clip_param=0.2,
        entropy_coef=0.001,
        num_learning_epochs=8,
        num_mini_batches=4,
        learning_rate=1.0e-3,
        schedule="adaptive",
        gamma=0.99,
        lam=0.95,
        desired_kl=0.01,
        max_grad_norm=1.0,
    )


def register_tasks() -> list[str]:
    """Register the external task(s) and preserve trainer Hydra arguments."""

    if TASK_ID not in gym.registry:
        gym.register(
            id=TASK_ID,
            entry_point=f"{RUNTIME_MODULE}:UR10ePegInsertEnv",
            disable_env_checker=True,
            kwargs={
                "env_cfg_entry_point": f"{__name__}:UR10ePegInsertEnvCfg",
                "rsl_rl_cfg_entry_point": f"{__name__}:UR10ePegInsertPPORunnerCfg",
            },
        )
    if PLAY_TASK_ID not in gym.registry:
        gym.register(
            id=PLAY_TASK_ID,
            entry_point=f"{RUNTIME_MODULE}:UR10ePegInsertEnv",
            disable_env_checker=True,
            kwargs={
                "env_cfg_entry_point": f"{__name__}:UR10ePegInsertEnvCfg_PLAY",
                "rsl_rl_cfg_entry_point": f"{__name__}:UR10ePegInsertPPORunnerCfg",
            },
        )
    # The callback consumes no command-line flags.  Returning the original
    # arguments keeps physics/renderer/Hydra overrides available to Isaac Lab.
    return list(sys.argv[1:])
