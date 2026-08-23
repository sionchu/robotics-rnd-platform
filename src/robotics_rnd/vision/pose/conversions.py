"""Explicit OpenCV Rodrigues/translation conversion at the vision boundary."""

from __future__ import annotations

from math import sqrt

import cv2
import numpy as np
from numpy.typing import NDArray

from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Quaternion, Transform, Vector3


def quaternion_from_rotation_matrix(matrix: NDArray[np.float64]) -> Quaternion:
    rotation = np.asarray(matrix, dtype=np.float64)
    if rotation.shape != (3, 3) or not np.isfinite(rotation).all():
        raise ValueError("rotation matrix must be finite with shape (3, 3)")
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-8) or not np.isclose(
        np.linalg.det(rotation), 1.0, atol=1e-8
    ):
        raise ValueError("rotation matrix must be orthonormal with determinant +1")
    trace = float(np.trace(rotation))
    if trace > 0.0:
        scale = sqrt(trace + 1.0) * 2.0
        w = 0.25 * scale
        x = (rotation[2, 1] - rotation[1, 2]) / scale
        y = (rotation[0, 2] - rotation[2, 0]) / scale
        z = (rotation[1, 0] - rotation[0, 1]) / scale
    elif rotation[0, 0] > rotation[1, 1] and rotation[0, 0] > rotation[2, 2]:
        scale = sqrt(1.0 + rotation[0, 0] - rotation[1, 1] - rotation[2, 2]) * 2.0
        w = (rotation[2, 1] - rotation[1, 2]) / scale
        x = 0.25 * scale
        y = (rotation[0, 1] + rotation[1, 0]) / scale
        z = (rotation[0, 2] + rotation[2, 0]) / scale
    elif rotation[1, 1] > rotation[2, 2]:
        scale = sqrt(1.0 + rotation[1, 1] - rotation[0, 0] - rotation[2, 2]) * 2.0
        w = (rotation[0, 2] - rotation[2, 0]) / scale
        x = (rotation[0, 1] + rotation[1, 0]) / scale
        y = 0.25 * scale
        z = (rotation[1, 2] + rotation[2, 1]) / scale
    else:
        scale = sqrt(1.0 + rotation[2, 2] - rotation[0, 0] - rotation[1, 1]) * 2.0
        w = (rotation[1, 0] - rotation[0, 1]) / scale
        x = (rotation[0, 2] + rotation[2, 0]) / scale
        y = (rotation[1, 2] + rotation[2, 1]) / scale
        z = 0.25 * scale
    return Quaternion(float(x), float(y), float(z), float(w))


def transform_from_rvec_tvec(
    rvec: NDArray[np.float64],
    tvec_m: NDArray[np.float64],
    *,
    target_frame: FrameId,
    source_frame: FrameId,
) -> Transform:
    """Convert OpenCV object-to-camera values into `T_target_source`."""

    rotation, _ = cv2.Rodrigues(np.asarray(rvec, dtype=np.float64).reshape(3, 1))
    translation = np.asarray(tvec_m, dtype=np.float64).reshape(3)
    if not np.isfinite(translation).all():
        raise ValueError("translation vector must contain finite metres")
    return Transform(
        target_frame=target_frame,
        source_frame=source_frame,
        translation_m=Vector3.from_iterable(translation),
        rotation=quaternion_from_rotation_matrix(np.asarray(rotation, dtype=np.float64)),
    )


def rvec_tvec_from_transform(
    transform: Transform,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    rvec, _ = cv2.Rodrigues(transform.rotation.as_rotation_matrix())
    return (
        np.asarray(rvec, dtype=np.float64).reshape(3, 1),
        transform.translation_m.as_array().reshape(3, 1),
    )
