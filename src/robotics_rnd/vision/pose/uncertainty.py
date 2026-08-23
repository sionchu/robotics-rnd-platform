"""Ground-truth pose errors for synthetic sensitivity studies."""

from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees, isfinite

import numpy as np

from robotics_rnd.core.geometry import Transform


@dataclass(frozen=True, slots=True)
class PoseErrorMetrics:
    translation_error_m: float
    relative_translation_error_percent: float
    orientation_error_rad: float
    mean_reprojection_error_px: float

    def __post_init__(self) -> None:
        values = (
            self.translation_error_m,
            self.relative_translation_error_percent,
            self.orientation_error_rad,
            self.mean_reprojection_error_px,
        )
        if not all(isfinite(value) and value >= 0.0 for value in values):
            raise ValueError("pose error metrics must be finite and non-negative")

    @property
    def orientation_error_deg(self) -> float:
        return degrees(self.orientation_error_rad)


def rotation_error_rad(estimate: Transform, expected: Transform) -> float:
    if estimate.target_frame != expected.target_frame or estimate.source_frame != expected.source_frame:
        raise ValueError("pose error requires matching transform frames")
    relative = estimate.rotation.as_rotation_matrix() @ expected.rotation.as_rotation_matrix().T
    cosine = float(np.clip((np.trace(relative) - 1.0) / 2.0, -1.0, 1.0))
    return acos(cosine)


def compare_pose(
    estimate: Transform,
    expected: Transform,
    *,
    mean_reprojection_error_px: float,
) -> PoseErrorMetrics:
    if estimate.target_frame != expected.target_frame or estimate.source_frame != expected.source_frame:
        raise ValueError("pose error requires matching transform frames")
    translation_delta = estimate.translation_m.as_array() - expected.translation_m.as_array()
    translation_error = float(np.linalg.norm(translation_delta))
    distance = float(np.linalg.norm(expected.translation_m.as_array()))
    relative = 100.0 * translation_error / max(distance, np.finfo(float).eps)
    return PoseErrorMetrics(
        translation_error_m=translation_error,
        relative_translation_error_percent=relative,
        orientation_error_rad=rotation_error_rad(estimate, expected),
        mean_reprojection_error_px=mean_reprojection_error_px,
    )
