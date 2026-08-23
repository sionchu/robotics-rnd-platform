"""Generic extrinsic and intrinsic calibration values."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import isfinite

import numpy as np
from numpy.typing import NDArray

from robotics_rnd.core import QualityMetric
from robotics_rnd.core.geometry import Transform
from robotics_rnd.vision.camera import CameraIntrinsics, DistortionCoefficients, ImageSize

from .metrics import ReprojectionMetrics


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    """Backward-compatible generic transform-calibration result from v0.1."""

    transform: Transform
    method: str
    validated: bool = False
    quality: tuple[QualityMetric, ...] = ()
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.method.strip():
            raise ValueError("calibration method is required")
        if self.created_at.tzinfo is None:
            raise ValueError("calibration timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CalibrationObservation:
    """One calibration view: object points in metres and image points in pixels."""

    observation_id: str
    image_size: ImageSize
    object_points_m: NDArray[np.float64]
    image_points_px: NDArray[np.float64]

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("calibration observation id is required")
        object_points = np.asarray(self.object_points_m, dtype=np.float64)
        image_points = np.asarray(self.image_points_px, dtype=np.float64)
        if object_points.ndim != 2 or object_points.shape[1] != 3:
            raise ValueError("object points must have shape (N, 3)")
        if image_points.ndim != 2 or image_points.shape[1] != 2:
            raise ValueError("image points must have shape (N, 2)")
        if len(object_points) < 4 or len(object_points) != len(image_points):
            raise ValueError("object and image point counts must match and contain at least four points")
        if not np.isfinite(object_points).all() or not np.isfinite(image_points).all():
            raise ValueError("calibration points must be finite")
        object_copy = object_points.copy()
        image_copy = image_points.copy()
        object_copy.flags.writeable = False
        image_copy.flags.writeable = False
        object.__setattr__(self, "object_points_m", object_copy)
        object.__setattr__(self, "image_points_px", image_copy)


@dataclass(frozen=True, slots=True)
class CameraCalibrationResult:
    """Validated pinhole calibration independent of the underlying solver objects."""

    intrinsics: CameraIntrinsics
    distortion: DistortionCoefficients
    metrics: ReprojectionMetrics
    method: str
    target: str
    accepted_observations: int
    rejected_observations: int = 0
    created_at: datetime = field(default_factory=_now)
    software_version: str = "unknown"

    def __post_init__(self) -> None:
        if not self.method.strip() or not self.target.strip():
            raise ValueError("calibration method and target are required")
        if self.accepted_observations <= 0 or self.rejected_observations < 0:
            raise ValueError("calibration observation counts are invalid")
        if self.created_at.tzinfo is None:
            raise ValueError("calibration timestamp must be timezone-aware")
        if not isfinite(self.metrics.rms_px):
            raise ValueError("calibration RMS must be finite")
