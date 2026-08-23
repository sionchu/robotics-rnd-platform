"""Generic fiducial observations with no OpenCV objects in the public API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite

import numpy as np

from robotics_rnd.core import FrameId, QualityMetric
from robotics_rnd.vision.camera import ImageSize

Pixel = tuple[float, float]


@dataclass(frozen=True, slots=True)
class AprilTagObservation:
    """Corners are clockwise: top-left, top-right, bottom-right, bottom-left."""

    tag_family: str
    tag_id: int
    corner_pixels: tuple[Pixel, Pixel, Pixel, Pixel]
    timestamp: datetime
    frame_id: FrameId
    image_size: ImageSize
    quality: tuple[QualityMetric, ...] = ()

    def __post_init__(self) -> None:
        if not self.tag_family.strip():
            raise ValueError("AprilTag family is required")
        if self.tag_id < 0:
            raise ValueError("AprilTag id must be non-negative")
        if self.timestamp.tzinfo is None:
            raise ValueError("AprilTag timestamp must be timezone-aware")
        corners = tuple((float(x), float(y)) for x, y in self.corner_pixels)
        if len(corners) != 4 or not all(isfinite(value) for point in corners for value in point):
            raise ValueError("AprilTag requires four finite pixel corners")
        array = np.asarray(corners, dtype=np.float64)
        signed_area = 0.5 * float(
            np.dot(array[:, 0], np.roll(array[:, 1], -1)) - np.dot(array[:, 1], np.roll(array[:, 0], -1))
        )
        if signed_area <= 0.0:
            raise ValueError("AprilTag corners must be clockwise in image coordinates")
        object.__setattr__(self, "corner_pixels", corners)

    @property
    def center_pixel(self) -> Pixel:
        array = np.asarray(self.corner_pixels, dtype=np.float64)
        center = np.mean(array, axis=0)
        return (float(center[0]), float(center[1]))

    @property
    def area_px2(self) -> float:
        array = np.asarray(self.corner_pixels, dtype=np.float64)
        return 0.5 * float(
            np.dot(array[:, 0], np.roll(array[:, 1], -1)) - np.dot(array[:, 1], np.roll(array[:, 0], -1))
        )
