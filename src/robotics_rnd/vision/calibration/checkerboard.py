"""CPU OpenCV checkerboard calibration promoted from experiment 001."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import cv2
import numpy as np
from numpy.typing import NDArray

from robotics_rnd.vision.camera import CameraIntrinsics, DistortionCoefficients

from .metrics import reprojection_metrics
from .models import CalibrationObservation, CameraCalibrationResult


@dataclass(frozen=True, slots=True)
class CheckerboardSpec:
    """Checkerboard inner-corner geometry in metres."""

    columns: int
    rows: int
    square_size_m: float

    def __post_init__(self) -> None:
        if self.columns < 2 or self.rows < 2:
            raise ValueError("checkerboard requires at least two rows and columns of inner corners")
        if not isfinite(self.square_size_m) or self.square_size_m <= 0.0:
            raise ValueError("checkerboard square size must be positive metres")

    @property
    def point_count(self) -> int:
        return self.columns * self.rows

    def object_points_m(self) -> NDArray[np.float64]:
        """Return centered planar points, ordered row-major from top-left."""

        grid = np.zeros((self.point_count, 3), dtype=np.float64)
        xy = np.mgrid[0 : self.columns, 0 : self.rows].T.reshape(-1, 2).astype(np.float64)
        xy[:, 0] -= (self.columns - 1) / 2.0
        xy[:, 1] -= (self.rows - 1) / 2.0
        grid[:, :2] = xy * self.square_size_m
        return grid


def calibrate_checkerboard(
    observations: tuple[CalibrationObservation, ...],
    board: CheckerboardSpec,
    *,
    minimum_observations: int = 8,
) -> CameraCalibrationResult:
    """Estimate pinhole intrinsics from validated checkerboard corner observations."""

    if len(observations) < minimum_observations:
        raise ValueError(f"calibration requires at least {minimum_observations} observations")
    image_size = observations[0].image_size
    for observation in observations:
        if observation.image_size != image_size:
            raise ValueError("all calibration observations must use one image size")
        if len(observation.object_points_m) != board.point_count:
            raise ValueError("observation point count does not match checkerboard")

    object_views = [np.asarray(item.object_points_m, dtype=np.float32) for item in observations]
    image_views = [np.asarray(item.image_points_px, dtype=np.float32) for item in observations]
    solver_rms, matrix, distortion, rvecs, tvecs = cv2.calibrateCamera(
        object_views,
        image_views,
        (image_size.width_px, image_size.height_px),
        None,
        None,
        flags=cv2.CALIB_FIX_K3,
    )
    projected_views: list[NDArray[np.float64]] = []
    for object_points, rvec, tvec in zip(object_views, rvecs, tvecs, strict=True):
        projected, _ = cv2.projectPoints(object_points, rvec, tvec, matrix, distortion)
        projected_views.append(np.asarray(projected, dtype=np.float64).reshape(-1, 2))
    metrics = reprojection_metrics(
        tuple(np.asarray(view, dtype=np.float64) for view in image_views),
        tuple(projected_views),
        float(solver_rms),
    )
    intrinsics = CameraIntrinsics(
        fx_px=float(matrix[0, 0]),
        fy_px=float(matrix[1, 1]),
        cx_px=float(matrix[0, 2]),
        cy_px=float(matrix[1, 2]),
        image_size=image_size,
    )
    coefficients = tuple(float(value) for value in np.asarray(distortion).reshape(-1))
    return CameraCalibrationResult(
        intrinsics=intrinsics,
        distortion=DistortionCoefficients(coefficients),
        metrics=metrics,
        method="opencv.calibrateCamera:CALIB_FIX_K3",
        target=(f"checkerboard:{board.columns}x{board.rows}:square_size_m={board.square_size_m:.9g}"),
        accepted_observations=len(observations),
        software_version=cv2.__version__,
    )
