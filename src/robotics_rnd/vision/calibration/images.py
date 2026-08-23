"""Checkerboard-corner extraction from generic captured/replayed images."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import cv2
import numpy as np

from robotics_rnd.vision.camera import ImageFrame

from .checkerboard import CheckerboardSpec
from .models import CalibrationObservation


@dataclass(frozen=True, slots=True)
class CheckerboardExtractionResult:
    observations: tuple[CalibrationObservation, ...]
    rejected_source_ids: tuple[str, ...]


def extract_checkerboard_observations(
    frames: Iterable[ImageFrame],
    board: CheckerboardSpec,
) -> CheckerboardExtractionResult:
    """Detect subpixel checkerboard corners while retaining rejected frame ids."""

    observations: list[CalibrationObservation] = []
    rejected: list[str] = []
    for index, frame in enumerate(frames):
        image = np.asarray(frame.image, dtype=np.uint8)
        gray = image
        if image.ndim == 3:
            conversion = cv2.COLOR_BGRA2GRAY if image.shape[2] == 4 else cv2.COLOR_BGR2GRAY
            gray = np.asarray(cv2.cvtColor(image, conversion), dtype=np.uint8)
        found, corners = cv2.findChessboardCornersSB(
            gray,
            (board.columns, board.rows),
            flags=cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY,
        )
        if not found or corners is None:
            rejected.append(frame.source_id)
            continue
        observations.append(
            CalibrationObservation(
                observation_id=f"{frame.source_id}-{index:06d}",
                image_size=frame.image_size,
                object_points_m=board.object_points_m(),
                image_points_px=np.asarray(corners, dtype=np.float64).reshape(-1, 2),
            )
        )
    return CheckerboardExtractionResult(tuple(observations), tuple(rejected))
