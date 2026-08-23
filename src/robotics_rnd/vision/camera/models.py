"""Pinhole-camera values with explicit pixel and distortion conventions."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

import numpy as np
from numpy.typing import NDArray

from robotics_rnd.core import FrameId

_DISTORTION_LENGTHS = frozenset({4, 5, 8, 12, 14})


@dataclass(frozen=True, slots=True)
class ImageSize:
    width_px: int
    height_px: int

    def __post_init__(self) -> None:
        if not isinstance(self.width_px, int) or not isinstance(self.height_px, int):
            raise TypeError("image dimensions must be integers")
        if self.width_px <= 0 or self.height_px <= 0:
            raise ValueError("image dimensions must be positive")

    @property
    def shape(self) -> tuple[int, int]:
        """NumPy image shape in `(height, width)` order."""

        return (self.height_px, self.width_px)


@dataclass(frozen=True, slots=True)
class CameraIntrinsics:
    """Pinhole intrinsics in pixels for one fixed image size."""

    fx_px: float
    fy_px: float
    cx_px: float
    cy_px: float
    image_size: ImageSize

    def __post_init__(self) -> None:
        values = tuple(float(value) for value in (self.fx_px, self.fy_px, self.cx_px, self.cy_px))
        if not all(isfinite(value) for value in values):
            raise ValueError("camera intrinsic values must be finite pixels")
        if values[0] <= 0.0 or values[1] <= 0.0:
            raise ValueError("camera focal lengths must be positive pixels")
        object.__setattr__(self, "fx_px", values[0])
        object.__setattr__(self, "fy_px", values[1])
        object.__setattr__(self, "cx_px", values[2])
        object.__setattr__(self, "cy_px", values[3])

    def as_matrix(self) -> NDArray[np.float64]:
        return np.array(
            [[self.fx_px, 0.0, self.cx_px], [0.0, self.fy_px, self.cy_px], [0.0, 0.0, 1.0]],
            dtype=np.float64,
        )


@dataclass(frozen=True, slots=True)
class DistortionCoefficients:
    """OpenCV radial/tangential coefficients in documented vector order."""

    values: tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0)
    model: str = "opencv_plumb_bob"

    def __post_init__(self) -> None:
        values = tuple(float(value) for value in self.values)
        if len(values) not in _DISTORTION_LENGTHS:
            raise ValueError("distortion must contain 4, 5, 8, 12, or 14 coefficients")
        if not all(isfinite(value) for value in values):
            raise ValueError("distortion coefficients must be finite")
        if not self.model.strip():
            raise ValueError("distortion model is required")
        object.__setattr__(self, "values", values)

    def as_array(self) -> NDArray[np.float64]:
        return np.asarray(self.values, dtype=np.float64).reshape(-1, 1)


@dataclass(frozen=True, slots=True)
class CameraModel:
    """A calibrated camera boundary; lengths outside image space remain metres."""

    intrinsics: CameraIntrinsics
    distortion: DistortionCoefficients = field(default_factory=DistortionCoefficients)
    frame_id: FrameId = field(default_factory=lambda: FrameId("camera"))

    @property
    def image_size(self) -> ImageSize:
        return self.intrinsics.image_size
