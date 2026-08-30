"""Kit-time runtime for Experiment 022's success-aligned axial task."""

from __future__ import annotations

import importlib
from typing import Any

import torch

base_learning_lab = importlib.import_module("experiments.robot.018_ur10e_peg_in_hole.learning_lab")
base_runtime = importlib.import_module("experiments.robot.021_ur10e_peg_in_hole_axial_credit.runtime")
registration = importlib.import_module(
    "experiments.robot.022_ur10e_peg_in_hole_success_aligned_axial.registration"
)

axial_remaining = base_runtime.axial_remaining


def success_aligned_axial_progress(env: Any) -> torch.Tensor:
    """Reward signed axial progress only inside the task's 3 mm success region."""

    current = axial_remaining(env)
    valid = getattr(env, "_tracker_valid", torch.zeros_like(current, dtype=torch.bool))
    previous = torch.where(valid, env._previous_axial_remaining, current)
    progress = previous - current
    xy_error = base_learning_lab._runtime_task_state(env)["xy_error"]
    value = progress * (xy_error <= registration.SUCCESS_LATERAL_M).float()
    env._previous_axial_remaining = current.detach()
    env._tracker_valid = torch.ones_like(valid)
    env._last_reward_axial = value.detach()
    return value


class SuccessAlignedAxialLearningLabWindow(base_learning_lab.LearningLabWindow):
    """The existing Learning UI with a minimal Experiment 022 gate panel."""

    def __init__(self, env: Any, window_name: str = "IsaacLab") -> None:
        self._axial_labels: dict[str, Any] = {}
        super().__init__(env, window_name)
        import omni.ui

        self._learning_labels["title"].text = "SUCCESS-ALIGNED AXIAL CREDIT"
        with (
            self.ui_window_elements["main_vstack"],
            omni.ui.CollapsableFrame(
                title="Experiment 022 Success-Aligned Axial Credit",
                width=omni.ui.Fraction(1),
                height=0,
                collapsed=False,
            ),
            omni.ui.VStack(spacing=4, height=0),
        ):
            self._axial_labels["gate"] = omni.ui.Label(
                f"Axial Gate: XY <= {registration.SUCCESS_LATERAL_M * 1000.0:.1f} mm",
                word_wrap=True,
            )
            self._axial_labels["flow"] = omni.ui.Label(
                "ALIGN <= 3 mm  ->  AXIAL CREDIT  ->  DESCEND  ->  SUCCESS",
                word_wrap=True,
            )
            self._axial_labels["remaining"] = omni.ui.Label("Axial Remaining: 0.0 mm", word_wrap=True)
            self._axial_labels["reward"] = omni.ui.Label(
                "Success-Aligned Axial Reward: +0.0000", word_wrap=True
            )

    def _update_ui(self) -> None:
        super()._update_ui()
        try:
            state = self._learning_env.task_state_for_ui()
            rewards = state["reward_terms"]
            axial_reward = rewards.get("success_aligned_axial_progress", state["axial_progress_reward"])
            self._axial_labels["remaining"].text = f"Axial Remaining: {state['axial_remaining_mm']:.1f} mm"
            self._axial_labels["reward"].text = f"Success-Aligned Axial Reward: {axial_reward:+.4f}"
            self._learning_labels["reward"].text = (
                f"Reward: alignment {rewards.get('alignment_progress', 0.0):+.4f} | "
                f"axial {axial_reward:+.4f} | "
                f"success {rewards.get('success_bonus', 0.0):+.4f} | "
                f"total {state['reward_total']:+.4f}"
            )
        except Exception:
            return


# Isaac Lab 3.0's explicit Kit visualizer path asks the canonical environment
# for this module-level class. Rebinding only the UI constructor keeps the
# physics, observations, actions, reset, and reward trajectories unchanged.
base_learning_lab.LearningLabWindow = SuccessAlignedAxialLearningLabWindow
base_learning_lab.TASK_ID = registration.TASK_ID
base_learning_lab.PLAY_TASK_ID = registration.PLAY_TASK_ID


class UR10eSuccessAlignedAxialEnv(base_runtime.UR10eAxialCreditEnv):
    """Experiment 021 runtime with only the axial reward predicate replaced."""

    pass
