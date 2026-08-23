"""Planar AprilTag PnP with explicit `T_camera_tag` output."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

import cv2
import numpy as np

from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Transform
from robotics_rnd.vision.camera import CameraModel
from robotics_rnd.vision.camera.synthetic import april_tag_object_corners_m
from robotics_rnd.vision.detection import AprilTagObservation

from .conversions import transform_from_rvec_tvec
from .reprojection import point_reprojection_errors_px, project_points


class PnPMethod(StrEnum):
    IPPE_SQUARE = "IPPE_SQUARE"
    ITERATIVE = "ITERATIVE"


@dataclass(frozen=True, slots=True)
class PnPResult:
    transform: Transform
    method: PnPMethod
    mean_reprojection_error_px: float
    max_reprojection_error_px: float
    point_reprojection_errors_px: tuple[float, ...]

    def __post_init__(self) -> None:
        values = (
            self.mean_reprojection_error_px,
            self.max_reprojection_error_px,
            *self.point_reprojection_errors_px,
        )
        if len(self.point_reprojection_errors_px) != 4:
            raise ValueError("AprilTag PnP requires four point errors")
        if not all(isfinite(value) and value >= 0.0 for value in values):
            raise ValueError("PnP reprojection errors must be finite non-negative pixels")


def _candidate_solutions(
    object_points_m: np.ndarray,
    image_points_px: np.ndarray,
    camera: CameraModel,
    method: PnPMethod,
) -> tuple[tuple[np.ndarray, np.ndarray, PnPMethod], ...]:
    flag = cv2.SOLVEPNP_IPPE_SQUARE if method is PnPMethod.IPPE_SQUARE else cv2.SOLVEPNP_ITERATIVE
    if method is PnPMethod.IPPE_SQUARE:
        result = cv2.solvePnPGeneric(
            object_points_m,
            image_points_px,
            camera.intrinsics.as_matrix(),
            camera.distortion.as_array(),
            flags=flag,
        )
        success = bool(result[0])
        if not success:
            return ()
        return tuple(
            (np.asarray(rvec, dtype=np.float64), np.asarray(tvec, dtype=np.float64), method)
            for rvec, tvec in zip(result[1], result[2], strict=True)
        )
    success, rvec, tvec = cv2.solvePnP(
        object_points_m,
        image_points_px,
        camera.intrinsics.as_matrix(),
        camera.distortion.as_array(),
        flags=flag,
    )
    return (
        ((np.asarray(rvec, dtype=np.float64), np.asarray(tvec, dtype=np.float64), method),) if success else ()
    )


def solve_apriltag_pnp(
    observation: AprilTagObservation,
    camera: CameraModel,
    tag_size_m: float,
    *,
    method: PnPMethod = PnPMethod.IPPE_SQUARE,
    tag_frame: FrameId | None = None,
) -> PnPResult:
    """Recover object-to-camera pose as `T_camera_tag`.

    OpenCV `rvec/tvec` satisfy `p_camera = R * p_tag + t`; this maps directly
    to the platform's `T_target_source` with target=camera and source=tag.
    """

    if observation.image_size != camera.image_size:
        raise ValueError("AprilTag observation and camera model image sizes must match")
    if observation.frame_id != camera.frame_id:
        raise ValueError("AprilTag observation and camera model frame ids must match")
    object_points = april_tag_object_corners_m(tag_size_m)
    image_points = np.asarray(observation.corner_pixels, dtype=np.float64)
    candidates = _candidate_solutions(object_points, image_points, camera, method)
    if not candidates:
        raise RuntimeError("OpenCV PnP did not return a valid pose")

    ranked: list[tuple[float, float, np.ndarray, np.ndarray, np.ndarray, PnPMethod]] = []
    for rvec, tvec, candidate_method in candidates:
        projected = project_points(object_points, rvec, tvec, camera)
        errors = point_reprojection_errors_px(image_points, projected)
        positive_depth_penalty = 0.0 if float(tvec.reshape(3)[2]) > 0.0 else 1.0e9
        ranked.append(
            (
                positive_depth_penalty + float(np.mean(errors)),
                float(np.max(errors)),
                rvec,
                tvec,
                errors,
                candidate_method,
            )
        )
    if method is PnPMethod.IPPE_SQUARE and min(item[0] for item in ranked) > 5.0:
        for rvec, tvec, candidate_method in _candidate_solutions(
            object_points, image_points, camera, PnPMethod.ITERATIVE
        ):
            projected = project_points(object_points, rvec, tvec, camera)
            errors = point_reprojection_errors_px(image_points, projected)
            ranked.append(
                (
                    float(np.mean(errors)),
                    float(np.max(errors)),
                    rvec,
                    tvec,
                    errors,
                    candidate_method,
                )
            )
    _, maximum, best_rvec, best_tvec, errors, selected_method = min(ranked, key=lambda item: item[0])
    source_frame = tag_frame or FrameId(f"apriltag_{observation.tag_family}_{observation.tag_id}")
    transform = transform_from_rvec_tvec(
        best_rvec,
        best_tvec,
        target_frame=observation.frame_id,
        source_frame=source_frame,
    )
    return PnPResult(
        transform=transform,
        method=selected_method,
        mean_reprojection_error_px=float(np.mean(errors)),
        max_reprojection_error_px=maximum,
        point_reprojection_errors_px=tuple(float(value) for value in errors),
    )
