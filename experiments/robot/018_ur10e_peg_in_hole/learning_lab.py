"""Experiment 018: an external manager-based UR10e peg-in-hole learning lab.

The task is intentionally kept outside Isaac Lab.  The upstream UR10e asset,
manager-based environment, differential IK action term, PhysX backend, and
RSL-RL trainer remain authoritative; this module only supplies the experiment
configuration, task registration callback, and a small native ``omni.ui``
window for the learning-lab probe.
"""

from __future__ import annotations

import argparse
import sys
import time
from contextlib import suppress

# The standalone Kit bootstrap must run before importing Isaac Lab modules.
# That intentional order is required by Isaac Sim's bundled Windows Python.
# ruff: noqa: E402

# Isaac Sim's bundled Python must start Kit before any Isaac Lab module that
# imports pxr is loaded.  The standalone path therefore parses its small CLI
# and launches AppLauncher first; the external trainer path only imports this
# module as a registration callback and does not launch an application here.
_BOOTSTRAP_ARGS = None
_BOOTSTRAP_APP = None
if __name__ == "__main__":
    from isaaclab.app import AppLauncher

    _bootstrap_parser = argparse.ArgumentParser(description="Experiment 018 UR10e peg-in-hole learning lab")
    _bootstrap_parser.add_argument("--task", default="Isaac-UR10e-PegInsert-Learning-v0")
    _bootstrap_parser.add_argument("--num_envs", type=int, default=1)
    _bootstrap_parser.add_argument("--steps", type=int, default=240)
    _bootstrap_parser.add_argument(
        "--mode", choices=["manual", "deterministic", "random"], default="deterministic"
    )
    AppLauncher.add_app_launcher_args(_bootstrap_parser)
    _BOOTSTRAP_ARGS = _bootstrap_parser.parse_args()
    _BOOTSTRAP_APP = AppLauncher(vars(_BOOTSTRAP_ARGS)).app

import copy
from collections.abc import Sequence
from typing import Any

import gymnasium as gym
import isaaclab.sim as sim_utils
import torch
from isaaclab.assets import ArticulationCfg, AssetBaseCfg
from isaaclab.controllers.differential_ik_cfg import DifferentialIKControllerCfg
from isaaclab.envs import ManagerBasedRLEnv, ManagerBasedRLEnvCfg
from isaaclab.envs.mdp.actions.actions_cfg import DifferentialInverseKinematicsActionCfg
from isaaclab.envs.mdp.events import reset_scene_to_default
from isaaclab.managers import ActionTermCfg as ActionTerm
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import ObservationGroupCfg as ObsGroup
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import TerminationTermCfg as DoneTerm
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sensors import ContactSensorCfg
from isaaclab.sim import CollisionPropertiesCfg
from isaaclab.utils import math as math_utils
from isaaclab.utils.configclass import configclass
from isaaclab_assets.robots.universal_robots import UR10e_CFG
from isaaclab_physx.physics import PhysxCfg
from isaaclab_rl.rsl_rl import RslRlMLPModelCfg, RslRlOnPolicyRunnerCfg, RslRlPpoAlgorithmCfg

TASK_ID = "Isaac-UR10e-PegInsert-Learning-v0"
PLAY_TASK_ID = "Isaac-UR10e-PegInsert-Learning-Play-v0"

# Geometry is deliberately primitive and dimensioned in SI units.  The XY
# location is the validated reachable fixture location from the UR10e probe.
PEG_WIDTH = 0.04
PEG_LENGTH = 0.12
HOLE_INNER = 0.05
WALL_THICKNESS = 0.02
HOLE_BOTTOM_Z = 0.02
HOLE_TOP_Z = 0.3061152
HOLE_DEPTH = HOLE_TOP_Z - HOLE_BOTTOM_Z
HOLE_CENTER_POS = (-0.6433276, -0.1740356, 0.0)

ACTION_SCALE_M = 0.005
RESET_XY_OFFSET_M = 0.015
APPROACH_HEIGHT_M = 0.025
ALIGNMENT_GATE_M = 0.010
SUCCESS_LATERAL_M = 0.005
SUCCESS_DEPTH_M = 0.060


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

    fixture_base = _static_box(
        "{ENV_REGEX_NS}/Fixture/Base",
        (_FIXTURE_SIZE, _FIXTURE_SIZE, 0.04),
        (HOLE_CENTER_POS[0], HOLE_CENTER_POS[1], 0.0),
        (0.24, 0.27, 0.32),
        collidable=True,
    )
    wall_x_neg = _static_box(
        "{ENV_REGEX_NS}/Fixture/HoleWallXNeg",
        (WALL_THICKNESS, _FIXTURE_SIZE, HOLE_DEPTH),
        (HOLE_CENTER_POS[0] - _WALL_OFFSET, HOLE_CENTER_POS[1], _WALL_Z),
        (0.32, 0.36, 0.42),
        collidable=True,
    )
    wall_x_pos = _static_box(
        "{ENV_REGEX_NS}/Fixture/HoleWallXPos",
        (WALL_THICKNESS, _FIXTURE_SIZE, HOLE_DEPTH),
        (HOLE_CENTER_POS[0] + _WALL_OFFSET, HOLE_CENTER_POS[1], _WALL_Z),
        (0.32, 0.36, 0.42),
        collidable=True,
    )
    wall_y_neg = _static_box(
        "{ENV_REGEX_NS}/Fixture/HoleWallYNeg",
        (HOLE_INNER, WALL_THICKNESS, HOLE_DEPTH),
        (HOLE_CENTER_POS[0], HOLE_CENTER_POS[1] - _WALL_OFFSET, _WALL_Z),
        (0.32, 0.36, 0.42),
        collidable=True,
    )
    wall_y_pos = _static_box(
        "{ENV_REGEX_NS}/Fixture/HoleWallYPos",
        (HOLE_INNER, WALL_THICKNESS, HOLE_DEPTH),
        (HOLE_CENTER_POS[0], HOLE_CENTER_POS[1] + _WALL_OFFSET, _WALL_Z),
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

    target_marker = _static_box(
        "{ENV_REGEX_NS}/Fixture/HoleTargetMarker",
        (0.012, 0.012, 0.012),
        (HOLE_CENTER_POS[0], HOLE_CENTER_POS[1], HOLE_TOP_Z + 0.006),
        (0.12, 0.86, 0.24),
        collidable=False,
    )
    insertion_axis_marker = _static_box(
        "{ENV_REGEX_NS}/Fixture/InsertionAxisMarker",
        (0.006, 0.006, HOLE_DEPTH),
        (HOLE_CENTER_POS[0], HOLE_CENTER_POS[1], HOLE_BOTTOM_Z + HOLE_DEPTH / 2.0),
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


def _wrist_body_id(env: Any) -> int:
    """Resolve the runtime wrist body once, after the articulation exists."""

    cached = getattr(env, "_wrist_body_id", None)
    if cached is not None:
        return cached
    body_ids, body_names = env.scene["robot"].find_bodies("wrist_3_link", preserve_order=True)
    if len(body_ids) != 1:
        raise RuntimeError(f"Expected one wrist_3_link body, found {body_names} ({body_ids}).")
    env._wrist_body_id = body_ids[0]
    return body_ids[0]


def _env_ids(env: Any, env_ids: Sequence[int] | torch.Tensor | slice | None) -> torch.Tensor:
    """Normalize manager reset indices to a device-local long tensor."""

    if env_ids is None or isinstance(env_ids, slice):
        return torch.arange(env.num_envs, device=env.device, dtype=torch.long)
    if isinstance(env_ids, torch.Tensor):
        return env_ids.to(device=env.device, dtype=torch.long)
    return torch.as_tensor(list(env_ids), device=env.device, dtype=torch.long)


def _runtime_task_state(env: Any) -> dict[str, torch.Tensor]:
    """Compute task frames and diagnostics from live articulation/sensor tensors."""

    robot = env.scene["robot"]
    body_id = _wrist_body_id(env)
    wrist_pos_w = robot.data.body_pos_w.torch[:, body_id]
    wrist_quat_w = robot.data.body_quat_w.torch[:, body_id]
    wrist_lin_vel_w = robot.data.body_lin_vel_w.torch[:, body_id]
    wrist_ang_vel_w = robot.data.body_ang_vel_w.torch[:, body_id]

    peg_offset_b = torch.zeros((env.num_envs, 3), device=env.device)
    peg_offset_b[:, 2] = PEG_LENGTH
    peg_offset_w = math_utils.quat_apply(wrist_quat_w, peg_offset_b)
    peg_tip_pos_w = wrist_pos_w + peg_offset_w
    peg_tip_vel_w = wrist_lin_vel_w + torch.cross(wrist_ang_vel_w, peg_offset_w, dim=-1)

    hole_center_w = env.scene.env_origins + torch.as_tensor(HOLE_CENTER_POS, device=env.device)
    peg_pos_rel_hole = peg_tip_pos_w - hole_center_w
    hole_top_z_w = hole_center_w[:, 2] + HOLE_TOP_Z
    insertion_depth = torch.clamp(hole_top_z_w - peg_tip_pos_w[:, 2], min=0.0, max=HOLE_DEPTH)
    xy_error = torch.linalg.norm(peg_pos_rel_hole[:, :2], dim=-1)
    z_error = peg_tip_pos_w[:, 2] - hole_top_z_w

    contact = env.scene["wrist_contact"].data.net_forces_w.torch
    if contact.ndim == 3:
        contact = contact[:, 0]
    contact_force = torch.linalg.norm(contact, dim=-1)

    return {
        "peg_pos_rel_hole": peg_pos_rel_hole,
        "peg_linear_velocity": peg_tip_vel_w,
        "insertion_depth": insertion_depth,
        "xy_error": xy_error,
        "z_error": z_error,
        "contact_force": contact_force,
        "peg_tip_pos_w": peg_tip_pos_w,
        "hole_center_w": hole_center_w,
    }


# Observation functions are deliberately small manager terms.  They resolve
# all state through the runtime scene; no USD transform cache is consulted.
def peg_pos_rel_hole(env: Any) -> torch.Tensor:
    return _runtime_task_state(env)["peg_pos_rel_hole"]


def peg_linear_velocity(env: Any) -> torch.Tensor:
    return _runtime_task_state(env)["peg_linear_velocity"]


def previous_action(env: Any) -> torch.Tensor:
    return env.action_manager.prev_action


def insertion_depth(env: Any) -> torch.Tensor:
    return _runtime_task_state(env)["insertion_depth"].unsqueeze(-1)


def success_termination(env: Any) -> torch.Tensor:
    state = _runtime_task_state(env)
    return (state["xy_error"] <= SUCCESS_LATERAL_M) & (state["insertion_depth"] >= SUCCESS_DEPTH_M)


def timeout_termination(env: Any) -> torch.Tensor:
    return env.episode_length_buf >= env.max_episode_length - 1


def alignment_progress(env: Any) -> torch.Tensor:
    current = _runtime_task_state(env)["xy_error"]
    valid = getattr(env, "_tracker_valid", torch.zeros_like(current, dtype=torch.bool))
    previous = torch.where(valid, env._previous_xy_error, current)
    value = previous - current
    env._previous_xy_error = current.detach()
    env._last_reward_alignment = value.detach()
    return value


def insertion_progress(env: Any) -> torch.Tensor:
    state = _runtime_task_state(env)
    current = state["insertion_depth"]
    valid = getattr(env, "_tracker_valid", torch.zeros_like(current, dtype=torch.bool))
    previous = torch.where(valid, env._previous_insertion_depth, current)
    value = (current - previous) * (state["xy_error"] <= ALIGNMENT_GATE_M).float()
    env._previous_insertion_depth = current.detach()
    env._last_reward_insertion = value.detach()
    env._tracker_valid = torch.ones_like(valid)
    return value


def success_bonus(env: Any) -> torch.Tensor:
    value = success_termination(env).float()
    env._last_reward_success = value.detach()
    return value


def reset_peg_insert(env: Any, env_ids: Sequence[int] | torch.Tensor | slice) -> None:
    """Reset above the fixture with only a small XY offset randomized.

    The nominal approach pose is solved from the official UR10e default pose
    with damped least-squares IK.  Its Z height is fixed at
    ``HOLE_TOP_Z + APPROACH_HEIGHT_M``; only the XY target is sampled, so the
    reset introduces no orientation, physics, or domain randomization.
    """

    # This is the upstream reset behavior for all scene entities, including
    # the robot's root and joints.  The offset below intentionally randomizes
    # only XY; the initial orientation remains the official UR10e orientation.
    reset_scene_to_default(env, env_ids)
    ids = _env_ids(env, env_ids)

    # Refresh the kinematic tensors at the official default pose before the
    # projection.  ``forward`` is not a simulation step.
    env.sim.forward()
    env.scene.update(dt=env.physics_dt)

    robot = env.scene["robot"]
    default_pos = robot.data.default_joint_pos.torch[ids].clone()
    default_vel = robot.data.default_joint_vel.torch[ids].clone()
    target_pos = env.scene.env_origins[ids].clone()
    target_pos += torch.as_tensor(
        (HOLE_CENTER_POS[0], HOLE_CENTER_POS[1], HOLE_TOP_Z + APPROACH_HEIGHT_M), device=env.device
    )
    target_pos[:, :2] += torch.empty((len(ids), 2), device=env.device).uniform_(
        -RESET_XY_OFFSET_M, RESET_XY_OFFSET_M
    )

    action_term = env.action_manager.get_term("arm_action")
    joint_pos = default_pos
    damping = (0.02**2) * torch.eye(6, device=env.device).expand(len(ids), -1, -1)
    # Iterate on live kinematic tensors rather than relying on a stale USD
    # transform cache.  The clamp keeps the startup projection conservative.
    for _ in range(8):
        robot.write_joint_position_to_sim_index(position=joint_pos, env_ids=ids)
        robot.write_joint_velocity_to_sim_index(velocity=default_vel, env_ids=ids)
        env.sim.forward()
        env.scene.update(dt=env.physics_dt)
        error = target_pos - _runtime_task_state(env)["peg_tip_pos_w"][ids]
        desired_delta = torch.zeros((len(ids), 6), device=env.device)
        desired_delta[:, :3] = torch.clamp(error, min=-0.08, max=0.08)
        jacobian = action_term._compute_frame_jacobian()[ids]
        dq = jacobian.transpose(1, 2) @ torch.linalg.solve(
            jacobian @ jacobian.transpose(1, 2) + damping, desired_delta.unsqueeze(-1)
        )
        joint_pos = joint_pos + dq.squeeze(-1)
        if hasattr(robot.data, "soft_joint_pos_limits"):
            limits = robot.data.soft_joint_pos_limits.torch[ids]
            joint_pos = torch.clamp(joint_pos, limits[..., 0], limits[..., 1])

    if hasattr(robot.data, "soft_joint_pos_limits"):
        limits = robot.data.soft_joint_pos_limits.torch[ids]
        joint_pos = torch.clamp(joint_pos, limits[..., 0], limits[..., 1])
    # Isaac Lab 3.0 exposes the indexed writers as the non-deprecated reset API.
    robot.write_joint_position_to_sim_index(position=joint_pos, env_ids=ids)
    robot.write_joint_velocity_to_sim_index(velocity=default_vel, env_ids=ids)
    robot.set_joint_position_target_index(target=joint_pos, env_ids=ids)


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
    """The three conceptual rewards used by v0."""

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


class LearningLabWindow:
    """Native Isaac UI window that presents the learning pipeline and live state."""

    def __init__(self, env: Any, window_name: str = "IsaacLab") -> None:
        import omni.kit.app
        import omni.ui
        from isaaclab.envs.ui.manager_based_rl_env_window import ManagerBasedRLEnvWindow

        print(f"[EXP018][ui] constructing native ManagerBasedRLEnvWindow window={window_name}", flush=True)
        # Delay the upstream UI import until after AppLauncher has started Kit.
        # Importing BaseEnvWindow before SimulationApp can load pxr extension
        # wrappers too early on the bundled Windows binary.
        self._base_window = ManagerBasedRLEnvWindow(env, window_name)
        self.ui_window = self._base_window.ui_window
        self.ui_window_elements = self._base_window.ui_window_elements
        self._learning_labels: dict[str, Any] = {}
        self._learning_env = env

        with (
            self.ui_window_elements["main_vstack"],
            omni.ui.CollapsableFrame(
                title="UR10e Peg-in-Hole Learning Lab",
                width=omni.ui.Fraction(1),
                height=0,
                collapsed=False,
            ),
            omni.ui.VStack(spacing=4, height=0),
        ):
            self._add_label("title", "UR10E PEG-IN-HOLE RL LAB")
            self._add_label(
                "pipeline",
                "Goal -> Observation (10) -> PPO Policy -> dX dY dZ -> Differential IK -> "
                "UR10e / PhysX -> Reward",
            )
            self._add_label("mode", "Mode: MANUAL")
            self._add_label("state", "State: waiting for reset")
            self._add_label("action", "Action: raw [0, 0, 0] | scaled [0, 0, 0] mm")
            self._add_label("reward", "Reward: alignment 0 | insertion 0 | success 0 | total 0")
            self._add_label(
                "terms",
                "Frames: robot base/root -> wrist_3_link -> peg tip; hole axes aligned to world. "
                "Units: m, m/s, N.",
            )

        app_interface = omni.kit.app.get_app_interface()
        self._update_handle = app_interface.get_post_update_event_stream().create_subscription_to_pop(
            lambda _event: self._update_ui()
        )

    def _add_label(self, key: str, text: str) -> None:
        import omni.ui

        self._learning_labels[key] = omni.ui.Label(text, word_wrap=True)

    def _update_ui(self) -> None:
        try:
            state = self._learning_env.task_state_for_ui()
            self._learning_labels["mode"].text = f"Mode: {state['mode']}"
            self._learning_labels["state"].text = (
                f"XY error {state['xy_error_mm']:.2f} mm | Z error {state['z_error_mm']:.2f} mm | "
                f"insertion {state['insertion_mm']:.2f} mm | contact {state['contact_force_n']:.1f} N | "
                f"episode step {state['episode_step']} | success {state['success']}"
            )
            self._learning_labels["action"].text = (
                f"Action: raw [{state['action_raw'][0]:+.2f}, {state['action_raw'][1]:+.2f}, "
                f"{state['action_raw'][2]:+.2f}] | scaled [{state['action_scaled_mm'][0]:+.2f}, "
                f"{state['action_scaled_mm'][1]:+.2f}, {state['action_scaled_mm'][2]:+.2f}] mm"
            )
            rewards = state["reward_terms"]
            self._learning_labels["reward"].text = (
                f"Reward: alignment {rewards.get('alignment_progress', 0.0):+.4f} | "
                f"insertion {rewards.get('insertion_progress', 0.0):+.4f} | "
                f"success {rewards.get('success_bonus', 0.0):+.4f} | total {state['reward_total']:+.4f}"
            )
        except Exception:
            # UI refresh must not interrupt simulation startup or stepping.
            return

    def __del__(self) -> None:
        handle = getattr(self, "_update_handle", None)
        if handle is not None:
            with suppress(Exception):
                handle.unsubscribe()
        with suppress(Exception):
            self._base_window = None


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
        self.viewer.lookat = (HOLE_CENTER_POS[0], HOLE_CENTER_POS[1], 0.18)
        self.ui_window_class_type = f"{__name__}:LearningLabWindow"


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


class UR10ePegInsertEnv(ManagerBasedRLEnv):
    """Manager-based task with runtime state helpers for the native learning UI."""

    _startup_evidence_printed = False

    def __init__(self, cfg: ManagerBasedRLEnvCfg, render_mode: str | None = None, **kwargs: Any):
        self._wrist_body_id: int | None = None
        self._learning_mode = "MANUAL"
        super().__init__(cfg=cfg, render_mode=render_mode, **kwargs)
        self._previous_xy_error = torch.zeros(self.num_envs, device=self.device)
        self._previous_insertion_depth = torch.zeros(self.num_envs, device=self.device)
        self._tracker_valid = torch.zeros(self.num_envs, device=self.device, dtype=torch.bool)
        self._last_reward_alignment = torch.zeros(self.num_envs, device=self.device)
        self._last_reward_insertion = torch.zeros(self.num_envs, device=self.device)
        self._last_reward_success = torch.zeros(self.num_envs, device=self.device)
        # Isaac Lab 3.0's explicit ``--viz kit`` path exposes a Kit visualizer
        # while leaving ``sim.has_gui`` false.  ManagerBasedEnv consequently
        # skips its legacy automatic window hook, so attach the same native
        # manager window explicitly when a visualizer is active.
        if self._window is None and self.sim.has_active_visualizers():
            self.setup_manager_visualizers()
            self._window = LearningLabWindow(self, window_name="IsaacLab")
        if not type(self)._startup_evidence_printed:
            obs_dim = self.observation_manager.group_obs_dim.get("policy", (None,))
            print(
                f"[EXP018] task={TASK_ID} robot=UR10e obs_dim={obs_dim} "
                f"action_dim={self.action_manager.total_action_dim} scale_m={ACTION_SCALE_M} "
                f"physics=PhysX dt_s={self.cfg.sim.dt} control_dt_s={self.step_dt} "
                f"decimation={self.cfg.decimation} peg_m={(PEG_WIDTH, PEG_WIDTH, PEG_LENGTH)} "
                f"hole_m={(HOLE_INNER, HOLE_DEPTH)} clearance_m={HOLE_INNER - PEG_WIDTH} "
                f"approach_height_m={APPROACH_HEIGHT_M} success_xy_m={SUCCESS_LATERAL_M} "
                f"success_depth_m={SUCCESS_DEPTH_M} timeout_s={self.cfg.episode_length_s}"
            )
            print(
                f"[EXP018] gui={self.sim.has_gui} "
                f"active_visualizers={self.sim.has_active_visualizers()} "
                f"ui_window_class={self.cfg.ui_window_class_type}"
            )
            type(self)._startup_evidence_printed = True

    def _reset_idx(self, env_ids: Sequence[int]) -> None:
        super()._reset_idx(env_ids)
        ids = _env_ids(self, env_ids)
        self._tracker_valid[ids] = False
        self._previous_xy_error[ids] = 0.0
        self._previous_insertion_depth[ids] = 0.0
        self._last_reward_alignment[ids] = 0.0
        self._last_reward_insertion[ids] = 0.0
        self._last_reward_success[ids] = 0.0

    def set_learning_mode(self, mode: str) -> None:
        self._learning_mode = mode.upper()

    @property
    def learning_mode(self) -> str:
        return self._learning_mode

    def task_state_for_ui(self) -> dict[str, Any]:
        state = _runtime_task_state(self)
        action = self.action_manager.action[0].detach()
        reward_total = float(self.reward_buf[0].detach().cpu().item()) if hasattr(self, "reward_buf") else 0.0
        reward_terms: dict[str, float] = {}
        with suppress(Exception):
            reward_terms = {
                name: float(values[0]) for name, values in self.reward_manager.get_active_iterable_terms(0)
            }
        return {
            "mode": self._learning_mode,
            "xy_error_mm": float(state["xy_error"][0].detach().cpu().item() * 1000.0),
            "z_error_mm": float(state["z_error"][0].detach().cpu().item() * 1000.0),
            "insertion_mm": float(state["insertion_depth"][0].detach().cpu().item() * 1000.0),
            "contact_force_n": float(state["contact_force"][0].detach().cpu().item()),
            "episode_step": int(self.episode_length_buf[0].detach().cpu().item()),
            "success": "YES" if bool(success_termination(self)[0].detach().cpu().item()) else "NO",
            "action_raw": [float(value) for value in action.cpu().tolist()],
            "action_scaled_mm": [float(value * ACTION_SCALE_M * 1000.0) for value in action.cpu().tolist()],
            "reward_terms": reward_terms,
            "reward_total": reward_total,
        }


def register_tasks() -> list[str]:
    """Register the external task(s) and preserve trainer Hydra arguments."""

    if TASK_ID not in gym.registry:
        gym.register(
            id=TASK_ID,
            entry_point=f"{__name__}:UR10ePegInsertEnv",
            disable_env_checker=True,
            kwargs={
                "env_cfg_entry_point": f"{__name__}:UR10ePegInsertEnvCfg",
                "rsl_rl_cfg_entry_point": f"{__name__}:UR10ePegInsertPPORunnerCfg",
            },
        )
    if PLAY_TASK_ID not in gym.registry:
        gym.register(
            id=PLAY_TASK_ID,
            entry_point=f"{__name__}:UR10ePegInsertEnv",
            disable_env_checker=True,
            kwargs={
                "env_cfg_entry_point": f"{__name__}:UR10ePegInsertEnvCfg_PLAY",
                "rsl_rl_cfg_entry_point": f"{__name__}:UR10ePegInsertPPORunnerCfg",
            },
        )
    # The callback consumes no command-line flags.  Returning the original
    # arguments keeps physics/renderer/Hydra overrides available to Isaac Lab.
    return list(sys.argv[1:])


def _axis_probe_action(env: UR10ePegInsertEnv, step: int) -> torch.Tensor:
    """Small deterministic axis pulses followed by a transparent hand-coded probe."""

    action = torch.zeros((env.num_envs, 3), device=env.device)
    pulse_axes = (
        (1.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, -1.0, 0.0),
        (0.0, 0.0, 1.0),
        (0.0, 0.0, -1.0),
    )
    pulse_length = 8
    if step < len(pulse_axes) * pulse_length:
        axis = pulse_axes[step // pulse_length]
        action[:] = torch.as_tensor(axis, device=env.device) * 0.5
        return action

    state = _runtime_task_state(env)
    # Root orientation is fixed to the official UR10e default, so the hole
    # frame and the robot-root frame share axes in this v0 probe.
    action[:, :2] = torch.clamp(-state["peg_pos_rel_hole"][:, :2] / ACTION_SCALE_M * 0.50, -1.0, 1.0)
    aligned = state["xy_error"] <= ALIGNMENT_GATE_M
    action[:, 2] = torch.where(
        aligned & (state["insertion_depth"] < SUCCESS_DEPTH_M),
        torch.full_like(state["insertion_depth"], -0.45),
        torch.zeros_like(state["insertion_depth"]),
    )
    return action


def _run_probe(args_cli: Any, simulation_app: Any) -> None:
    """Run a finite GUI/manual or deterministic/random learning-lab probe."""

    try:
        register_tasks()
        from isaaclab_tasks.utils import parse_env_cfg

        env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=args_cli.num_envs)
        env_cfg.env_name = args_cli.task
        env = gym.make(args_cli.task, cfg=env_cfg).unwrapped
        env.set_learning_mode(args_cli.mode)
        env.reset(seed=42)

        start = time.perf_counter()
        for step in range(args_cli.steps):
            with torch.inference_mode():
                if args_cli.mode == "random":
                    action = torch.empty((env.num_envs, 3), device=env.device).uniform_(-0.3, 0.3)
                elif args_cli.mode == "deterministic":
                    action = _axis_probe_action(env, step)
                else:
                    action = torch.zeros((env.num_envs, 3), device=env.device)
                _, reward, terminated, truncated, _ = env.step(action)
            if step % 20 == 0 or bool(torch.any(terminated | truncated)):
                state = env.task_state_for_ui()
                print(
                    "[EXP018][probe] step={} xy_mm={:.3f} z_error_mm={:.3f} insertion_mm={:.3f} "
                    "contact_n={:.2f} reward={:.5f} "
                    "terminated={} truncated={}".format(
                        step,
                        state["xy_error_mm"],
                        state["z_error_mm"],
                        state["insertion_mm"],
                        state["contact_force_n"],
                        float(reward[0].detach().cpu().item()),
                        bool(terminated[0].detach().cpu().item()),
                        bool(truncated[0].detach().cpu().item()),
                    )
                )
            if not simulation_app.is_running():
                break
        print(f"[EXP018] probe_elapsed_s={time.perf_counter() - start:.3f}")
    except BaseException as exc:
        print(f"[EXP018][error] {type(exc).__name__}: {exc}", flush=True)
        raise
    finally:
        if "env" in locals():
            env.close()
        simulation_app.close()


if __name__ == "__main__":
    _run_probe(_BOOTSTRAP_ARGS, _BOOTSTRAP_APP)
