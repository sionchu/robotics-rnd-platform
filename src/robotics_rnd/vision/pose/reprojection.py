"""Projection and pixel-error helpers for calibrated pose estimates."""

from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

from robotics_rnd.vision.camera import CameraModel


def project_points(
    object_points_m: NDArray[np.float64],
    rvec: NDArray[np.float64],
    tvec_m: NDArray[np.float64],
    camera: CameraModel,
) -> NDArray[np.float64]:
    points = np.asarray(object_points_m, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("object points must be finite with shape (N, 3)")
    projected, _ = cv2.projectPoints(
        points,
        np.asarray(rvec, dtype=np.float64).reshape(3, 1),
        np.asarray(tvec_m, dtype=np.float64).reshape(3, 1),
        camera.intrinsics.as_matrix(),
        camera.distortion.as_array(),
    )
    return np.asarray(projected, dtype=np.float64).reshape(-1, 2)


def point_reprojection_errors_px(
    observed_px: NDArray[np.float64], projected_px: NDArray[np.float64]
) -> NDArray[np.float64]:
    observed = np.asarray(observed_px, dtype=np.float64)
    projected = np.asarray(projected_px, dtype=np.float64)
    if observed.shape != projected.shape or observed.ndim != 2 or observed.shape[1] != 2:
        raise ValueError("observed and projected pixels must share shape (N, 2)")
    return np.linalg.norm(observed - projected, axis=1)
