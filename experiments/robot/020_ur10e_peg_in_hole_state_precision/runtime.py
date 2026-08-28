"""Kit-time alias for the canonical Experiment 018 UR10e runtime."""

from __future__ import annotations

import importlib

base_learning_lab = importlib.import_module("experiments.robot.018_ur10e_peg_in_hole.learning_lab")
registration = importlib.import_module("experiments.robot.020_ur10e_peg_in_hole_state_precision.registration")

# Keep the runtime implementation single-sourced while binding this process to
# the 46 mm / 3 mm Experiment 020 geometry and task identity.
base_learning_lab.TASK_ID = registration.TASK_ID
base_learning_lab.PLAY_TASK_ID = registration.PLAY_TASK_ID
base_learning_lab.HOLE_INNER = registration.HOLE_INNER
base_learning_lab.SUCCESS_LATERAL_M = registration.SUCCESS_LATERAL_M

UR10eStatePrecisionEnv = base_learning_lab.UR10ePegInsertEnv
LearningLabWindow = base_learning_lab.LearningLabWindow
