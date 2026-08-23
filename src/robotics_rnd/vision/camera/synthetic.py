"""Deterministic synthetic camera data for calibration and tag research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import isfinite

import cv2
import numpy as np
from numpy.typing import NDArray

from robotics_rnd.core import FrameId
from robotics_rnd.vision.calibration.checkerboard import CheckerboardSpec
from robotics_rnd.vision.calibration.models import CalibrationObservation

from .models import CameraModel
from .sources import ImageFrame


@dataclass(frozen=True, slots=True)
class SyntheticCalibrationDataset:
    observations: tuple[CalibrationObservation, ...]
    ground_truth: CameraModel
    seed: int
    pixel_noise_std_px: float
    rejected_proposals: int


def generate_checkerboard_observations(
    camera: CameraModel,
    board: CheckerboardSpec,
    *,
    views: int = 24,
    seed: int = 20260823,
    pixel_noise_std_px: float = 0.15,
    margin_px: float = 20.0,
) -> SyntheticCalibrationDataset:
    """Generate diverse, fully visible checkerboard observations with known truth."""

    if views < 8:
        raise ValueError("synthetic calibration requires at least eight views")
    if not isfinite(pixel_noise_std_px) or pixel_noise_std_px < 0.0:
        raise ValueError("pixel noise must be finite and non-negative")
    if not isfinite(margin_px) or margin_px < 0.0:
        raise ValueError("image margin must be finite and non-negative")
    rng = np.random.default_rng(seed)
    object_points = board.object_points_m()
    observations: list[CalibrationObservation] = []
    rejected = 0
    maximum_proposals = views * 200
    for _proposal in range(maximum_proposals):
        rvec = rng.uniform((-0.45, -0.45, -0.65), (0.45, 0.45, 0.65)).astype(np.float64)
        tvec = np.array(
            [rng.uniform(-0.13, 0.13), rng.uniform(-0.09, 0.09), rng.uniform(0.55, 1.15)],
            dtype=np.float64,
        )
        projected, _ = cv2.projectPoints(
            object_points,
            rvec,
            tvec,
            camera.intrinsics.as_matrix(),
            camera.distortion.as_array(),
        )
        image_points = np.asarray(projected, dtype=np.float64).reshape(-1, 2)
        width, height = camera.image_size.width_px, camera.image_size.height_px
        visible = (
            np.min(image_points[:, 0]) >= margin_px
            and np.max(image_points[:, 0]) <= width - margin_px
            and np.min(image_points[:, 1]) >= margin_px
            and np.max(image_points[:, 1]) <= height - margin_px
        )
        if not visible:
            rejected += 1
            continue
        if pixel_noise_std_px:
            image_points += rng.normal(0.0, pixel_noise_std_px, image_points.shape)
        observations.append(
            CalibrationObservation(
                observation_id=f"synthetic-checkerboard-{len(observations):03d}",
                image_size=camera.image_size,
                object_points_m=object_points,
                image_points_px=image_points,
            )
        )
        if len(observations) == views:
            break
    if len(observations) != views:
        raise RuntimeError(f"generated only {len(observations)} visible views from {maximum_proposals}")
    return SyntheticCalibrationDataset(
        observations=tuple(observations),
        ground_truth=camera,
        seed=seed,
        pixel_noise_std_px=pixel_noise_std_px,
        rejected_proposals=rejected,
    )


def april_tag_object_corners_m(tag_size_m: float) -> NDArray[np.float64]:
    """IPPE square order: top-left, top-right, bottom-right, bottom-left.

    The tag frame is right-handed with +x right, +y up, and +z out of the
    printed front. A front-facing tag therefore has a 180-degree camera-X
    rotation in OpenCV's x-right, y-down, z-forward camera frame.
    """

    if not isfinite(tag_size_m) or tag_size_m <= 0.0:
        raise ValueError("AprilTag size must be positive metres")
    half = tag_size_m / 2.0
    return np.array(
        [[-half, half, 0.0], [half, half, 0.0], [half, -half, 0.0], [-half, -half, 0.0]],
        dtype=np.float64,
    )


def render_apriltag_frame(
    camera: CameraModel,
    *,
    tag_id: int,
    tag_size_m: float,
    rvec_tag_to_camera: NDArray[np.float64],
    tvec_tag_to_camera_m: NDArray[np.float64],
    family_dictionary: int = cv2.aruco.DICT_APRILTAG_36h11,
    marker_pixels: int = 256,
    blur_sigma_px: float = 0.0,
    image_noise_std: float = 0.0,
    seed: int = 20260823,
    source_id: str = "synthetic-apriltag",
    timestamp_offset_ms: int = 0,
) -> ImageFrame:
    """Render one perspective AprilTag image from an explicit object-to-camera pose."""

    if marker_pixels < 32:
        raise ValueError("marker raster must be at least 32 pixels")
    if blur_sigma_px < 0.0 or image_noise_std < 0.0:
        raise ValueError("blur and image noise must be non-negative")
    object_points = april_tag_object_corners_m(tag_size_m)
    projected, _ = cv2.projectPoints(
        object_points,
        np.asarray(rvec_tag_to_camera, dtype=np.float64).reshape(3, 1),
        np.asarray(tvec_tag_to_camera_m, dtype=np.float64).reshape(3, 1),
        camera.intrinsics.as_matrix(),
        camera.distortion.as_array(),
    )
    destination = np.asarray(projected, dtype=np.float32).reshape(4, 2)
    width, height = camera.image_size.width_px, camera.image_size.height_px
    if (
        np.min(destination[:, 0]) < 2.0
        or np.max(destination[:, 0]) >= width - 2.0
        or np.min(destination[:, 1]) < 2.0
        or np.max(destination[:, 1]) >= height - 2.0
    ):
        raise ValueError("projected AprilTag must fit inside the image")
    dictionary = cv2.aruco.getPredefinedDictionary(family_dictionary)
    marker = cv2.aruco.generateImageMarker(dictionary, tag_id, marker_pixels)
    source = np.array(
        [
            [0.0, 0.0],
            [marker_pixels - 1.0, 0.0],
            [marker_pixels - 1.0, marker_pixels - 1.0],
            [0.0, marker_pixels - 1.0],
        ],
        dtype=np.float32,
    )
    homography = cv2.getPerspectiveTransform(source, destination)
    image = cv2.warpPerspective(
        marker,
        homography,
        (width, height),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )
    if blur_sigma_px > 0.0:
        image = cv2.GaussianBlur(image, (0, 0), blur_sigma_px)
    if image_noise_std > 0.0:
        rng = np.random.default_rng(seed)
        noisy = image.astype(np.float64) + rng.normal(0.0, image_noise_std, image.shape)
        image = np.clip(noisy, 0.0, 255.0).astype(np.uint8)
    timestamp = datetime(2026, 8, 23, tzinfo=UTC) + timedelta(milliseconds=timestamp_offset_ms)
    image_uint8: NDArray[np.uint8] = np.asarray(image, dtype=np.uint8)
    return ImageFrame(FrameId("camera"), timestamp, image_uint8, source_id)
