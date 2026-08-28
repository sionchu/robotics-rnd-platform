"""Kit-time runtime for the Experiment 021 axial-credit task."""

from __future__ import annotations

import importlib
from typing import Any

import torch

base_learning_lab = importlib.import_module("experiments.robot.018_ur10e_peg_in_hole.learning_lab")
base_runtime = importlib.import_module("experiments.robot.020_ur10e_peg_in_hole_state_precision.runtime")
registration = importlib.import_module("experiments.robot.021_ur10e_peg_in_hole_axial_credit.registration")


def axial_remaining(env: Any) -> torch.Tensor:
    """Return meters remaining from the peg tip to the 60 mm success target."""

    state = base_learning_lab._runtime_task_state(env)
    success_target_z = (
        state["hole_center_w"][:, 2] + base_learning_lab.HOLE_TOP_Z - base_learning_lab.SUCCESS_DEPTH_M
    )
    return torch.clamp(state["peg_tip_pos_w"][:, 2] - success_target_z, min=0.0)


def gated_axial_progress(env: Any) -> torch.Tensor:
    """Reward signed downward progress toward the success-depth target."""

    current = axial_remaining(env)
    valid = getattr(env, "_axial_tracker_valid", torch.zeros_like(current, dtype=torch.bool))
    previous = torch.where(valid, env._previous_axial_remaining, current)
    progress = previous - current
    value = (
        progress
        * (
            base_learning_lab._runtime_task_state(env)["xy_error"] <= base_learning_lab.ALIGNMENT_GATE_M
        ).float()
    )
    env._previous_axial_remaining = current.detach()
    env._axial_tracker_valid = torch.ones_like(valid)
    env._last_reward_axial = value.detach()
    return value


class UR10eAxialCreditEnv(base_runtime.UR10eStatePrecisionEnv):
    """Experiment 020 environment with one additional reward tracker."""

    _startup_evidence_printed = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._previous_axial_remaining = torch.zeros(self.num_envs, device=self.device)
        self._axial_tracker_valid = torch.zeros(self.num_envs, device=self.device, dtype=torch.bool)
        self._last_reward_axial = torch.zeros(self.num_envs, device=self.device)

    def _reset_idx(self, env_ids: Any) -> None:
        super()._reset_idx(env_ids)
        ids = base_learning_lab._env_ids(self, env_ids)
        self._previous_axial_remaining[ids] = 0.0
        self._axial_tracker_valid[ids] = False
        self._last_reward_axial[ids] = 0.0

    def task_state_for_ui(self) -> dict[str, Any]:
        state = super().task_state_for_ui()
        runtime_state = base_learning_lab._runtime_task_state(self)
        state["peg_z_mm"] = float(runtime_state["peg_tip_pos_w"][0, 2].detach().cpu().item() * 1000.0)
        state["axial_remaining_mm"] = float(axial_remaining(self)[0].detach().cpu().item() * 1000.0)
        state["axial_progress_reward"] = float(self._last_reward_axial[0].detach().cpu().item())
        return state


class AxialCreditLearningLabWindow(base_learning_lab.LearningLabWindow):
    """Existing Learning UI with the two axial-credit values added."""

    def __init__(self, env: Any, window_name: str = "IsaacLab") -> None:
        self._axial_labels: dict[str, Any] = {}
        super().__init__(env, window_name)
        import omni.ui

        with (
            self.ui_window_elements["main_vstack"],
            omni.ui.CollapsableFrame(
                title="Experiment 021 Axial Credit",
                width=omni.ui.Fraction(1),
                height=0,
                collapsed=False,
            ),
            omni.ui.VStack(spacing=4, height=0),
        ):
            self._axial_labels["flow"] = omni.ui.Label(
                "ALIGN  ↓  AXIAL APPROACH  ↓  INSERT  ↓  SUCCESS",
                word_wrap=True,
            )
            self._axial_labels["remaining"] = omni.ui.Label("Axial Remaining: 0.0 mm", word_wrap=True)
            self._axial_labels["reward"] = omni.ui.Label("Axial Progress Reward: +0.0000", word_wrap=True)

    def _update_ui(self) -> None:
        super()._update_ui()
        try:
            state = self._learning_env.task_state_for_ui()
            rewards = state["reward_terms"]
            axial_reward = rewards.get("gated_axial_progress", state["axial_progress_reward"])
            self._axial_labels["remaining"].text = f"Axial Remaining: {state['axial_remaining_mm']:.1f} mm"
            self._axial_labels["reward"].text = f"Axial Progress Reward: {axial_reward:+.4f}"
            self._learning_labels["reward"].text = (
                f"Reward: alignment {rewards.get('alignment_progress', 0.0):+.4f} | "
                f"axial {axial_reward:+.4f} | "
                f"success {rewards.get('success_bonus', 0.0):+.4f} | total {state['reward_total']:+.4f}"
            )
        except Exception:
            return
