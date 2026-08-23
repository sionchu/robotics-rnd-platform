import math
from datetime import UTC, datetime

import numpy as np
import pytest

from robotics_rnd.core import FrameId
from robotics_rnd.vision.camera import CameraIntrinsics, CameraModel, DistortionCoefficients, ImageSize
from robotics_rnd.vision.camera.synthetic import april_tag_object_corners_m
from robotics_rnd.vision.detection import AprilTagObservation
from robotics_rnd.vision.pose import (
    PnPMethod,
    compare_pose,
    solve_apriltag_pnp,
    transform_from_rvec_tvec,
)
from robotics_rnd.vision.pose.reprojection import project_points


def camera_model() -> CameraModel:
    size = ImageSize(1280, 720)
    return CameraModel(
        CameraIntrinsics(920.0, 915.0, 640.0, 360.0, size),
        DistortionCoefficients(),
        FrameId("camera"),
    )


def observation_from_pose(camera: CameraModel, rvec: np.ndarray, tvec_m: np.ndarray) -> AprilTagObservation:
    projected = project_points(april_tag_object_corners_m(0.12), rvec, tvec_m, camera)
    corners = tuple((float(x), float(y)) for x, y in projected)
    return AprilTagObservation(
        "tag36h11",
        7,
        corners,
        datetime(2026, 8, 23, tzinfo=UTC),
        camera.frame_id,
        camera.image_size,
    )


@pytest.mark.parametrize(
    ("rvec", "tvec"),
    [
        (np.array([math.pi, 0.0, 0.0]), np.array([0.0, 0.0, 0.8])),
        (np.array([math.pi - 0.20, 0.12, 0.08]), np.array([0.03, -0.02, 0.8])),
        (np.array([math.pi - 0.45, -0.18, 0.16]), np.array([-0.08, 0.04, 1.2])),
    ],
)
def test_known_pose_is_recovered_with_explicit_transform_direction(
    rvec: np.ndarray, tvec: np.ndarray
) -> None:
    camera = camera_model()
    tag_frame = FrameId("tag")
    observation = observation_from_pose(camera, rvec, tvec)
    result = solve_apriltag_pnp(observation, camera, 0.12, tag_frame=tag_frame)
    expected = transform_from_rvec_tvec(
        rvec,
        tvec,
        target_frame=FrameId("camera"),
        source_frame=tag_frame,
    )
    metrics = compare_pose(
        result.transform,
        expected,
        mean_reprojection_error_px=result.mean_reprojection_error_px,
    )

    assert result.transform.name == "T_camera_tag"
    assert metrics.translation_error_m < 1.0e-8
    assert metrics.orientation_error_rad < 1.0e-7
    assert metrics.mean_reprojection_error_px < 1.0e-7


def test_iterative_method_and_invalid_inputs() -> None:
    camera = camera_model()
    observation = observation_from_pose(
        camera,
        np.array([math.pi - 0.2, 0.1, 0.05]),
        np.array([0.0, 0.0, 0.9]),
    )
    result = solve_apriltag_pnp(observation, camera, 0.12, method=PnPMethod.ITERATIVE)
    assert result.method is PnPMethod.ITERATIVE
    with pytest.raises(ValueError, match="positive metres"):
        solve_apriltag_pnp(observation, camera, 0.0)

    wrong_size_camera = CameraModel(
        CameraIntrinsics(920.0, 915.0, 320.0, 240.0, ImageSize(640, 480)),
        DistortionCoefficients(),
        FrameId("camera"),
    )
    with pytest.raises(ValueError, match="image sizes"):
        solve_apriltag_pnp(observation, wrong_size_camera, 0.12)
