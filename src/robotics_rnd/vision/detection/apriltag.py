"""CPU OpenCV AprilTag detector promoted from experiment 002."""

from __future__ import annotations

from math import hypot
from typing import cast

import cv2
import numpy as np
from numpy.typing import NDArray

from robotics_rnd.core import QualityMetric
from robotics_rnd.vision.camera import ImageFrame

from .models import AprilTagObservation, Pixel

_FAMILIES = {
    "tag16h5": cv2.aruco.DICT_APRILTAG_16h5,
    "tag25h9": cv2.aruco.DICT_APRILTAG_25h9,
    "tag36h10": cv2.aruco.DICT_APRILTAG_36h10,
    "tag36h11": cv2.aruco.DICT_APRILTAG_36h11,
}


class OpenCvAprilTagDetector:
    """Return platform observations; OpenCV arrays never cross this boundary."""

    def __init__(self, family: str = "tag36h11") -> None:
        normalized = family.lower()
        if normalized not in _FAMILIES:
            raise ValueError(f"unsupported AprilTag family: {family}")
        self.family = normalized
        dictionary = cv2.aruco.getPredefinedDictionary(_FAMILIES[normalized])
        parameters = cv2.aruco.DetectorParameters()
        self._detector = cv2.aruco.ArucoDetector(dictionary, parameters)

    @property
    def dependency_version(self) -> str:
        return cv2.__version__

    def detect(self, frame: ImageFrame) -> tuple[AprilTagObservation, ...]:
        image: NDArray[np.uint8] = np.asarray(frame.image, dtype=np.uint8)
        if image.ndim == 3:
            color_code = cv2.COLOR_BGRA2GRAY if image.shape[2] == 4 else cv2.COLOR_BGR2GRAY
            image = np.asarray(cv2.cvtColor(image, color_code), dtype=np.uint8)
        corners, ids, _rejected = self._detector.detectMarkers(image)
        if ids is None:
            return ()
        observations: list[AprilTagObservation] = []
        for raw_corners, raw_id in zip(corners, ids.reshape(-1), strict=True):
            points = np.asarray(raw_corners, dtype=np.float64).reshape(4, 2)
            corner_tuple = cast(
                tuple[Pixel, Pixel, Pixel, Pixel],
                tuple((float(point[0]), float(point[1])) for point in points),
            )
            perimeter = sum(
                hypot(
                    corner_tuple[(index + 1) % 4][0] - corner_tuple[index][0],
                    corner_tuple[(index + 1) % 4][1] - corner_tuple[index][1],
                )
                for index in range(4)
            )
            area = abs(float(cv2.contourArea(points.astype(np.float32))))
            observations.append(
                AprilTagObservation(
                    tag_family=self.family,
                    tag_id=int(raw_id),
                    corner_pixels=corner_tuple,
                    timestamp=frame.timestamp,
                    frame_id=frame.frame_id,
                    image_size=frame.image_size,
                    quality=(
                        QualityMetric("quad_perimeter", perimeter, "px"),
                        QualityMetric("quad_area", area, "px^2"),
                    ),
                )
            )
        return tuple(sorted(observations, key=lambda item: item.tag_id))
