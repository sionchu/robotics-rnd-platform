from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from robotics_rnd.core import FrameId
from robotics_rnd.vision.calibration import (
    CalibrationObservation,
    CheckerboardSpec,
    calibrate_checkerboard,
    extract_checkerboard_observations,
    load_calibration_json,
    save_calibration_json,
)
from robotics_rnd.vision.camera import (
    CameraIntrinsics,
    CameraModel,
    DistortionCoefficients,
    ImageFrame,
    ImageSize,
)
from robotics_rnd.vision.camera.synthetic import generate_checkerboard_observations


def calibrated_truth() -> CameraModel:
    size = ImageSize(1280, 720)
    return CameraModel(
        CameraIntrinsics(920.0, 915.0, 640.0, 360.0, size),
        DistortionCoefficients((-0.08, 0.03, 0.0005, -0.0003, 0.0)),
        FrameId("camera"),
    )


def test_noisy_synthetic_calibration_recovers_known_intrinsics() -> None:
    truth = calibrated_truth()
    board = CheckerboardSpec(9, 6, 0.03)
    dataset = generate_checkerboard_observations(
        truth,
        board,
        views=28,
        seed=20260823,
        pixel_noise_std_px=0.15,
    )
    result = calibrate_checkerboard(dataset.observations, board)

    assert abs(result.intrinsics.fx_px - truth.intrinsics.fx_px) / truth.intrinsics.fx_px < 0.005
    assert abs(result.intrinsics.fy_px - truth.intrinsics.fy_px) / truth.intrinsics.fy_px < 0.005
    principal_point_error = np.linalg.norm(
        [
            result.intrinsics.cx_px - truth.intrinsics.cx_px,
            result.intrinsics.cy_px - truth.intrinsics.cy_px,
        ]
    )
    assert principal_point_error < 2.0
    assert result.metrics.mean_px < 0.3
    assert result.metrics.rms_px < 0.3
    assert result.accepted_observations == 28
    assert result.rejected_observations == 0


def test_calibration_persistence_round_trip(tmp_path: Path) -> None:
    truth = calibrated_truth()
    board = CheckerboardSpec(9, 6, 0.03)
    dataset = generate_checkerboard_observations(truth, board, views=12, seed=7, pixel_noise_std_px=0.0)
    result = calibrate_checkerboard(dataset.observations, board)
    path = tmp_path / "calibration.json"
    save_calibration_json(result, path)
    loaded = load_calibration_json(path)

    assert loaded.intrinsics == result.intrinsics
    assert loaded.distortion == result.distortion
    assert loaded.metrics == result.metrics
    assert loaded.target == result.target
    assert loaded.accepted_observations == result.accepted_observations


def test_calibration_rejects_insufficient_or_inconsistent_observations() -> None:
    truth = calibrated_truth()
    board = CheckerboardSpec(9, 6, 0.03)
    dataset = generate_checkerboard_observations(truth, board, views=8, seed=8)
    with pytest.raises(ValueError, match="at least 9"):
        calibrate_checkerboard(dataset.observations, board, minimum_observations=9)

    wrong_size = CalibrationObservation(
        "wrong-size",
        ImageSize(640, 480),
        dataset.observations[0].object_points_m,
        dataset.observations[0].image_points_px,
    )
    with pytest.raises(ValueError, match="one image size"):
        calibrate_checkerboard((*dataset.observations[:-1], wrong_size), board)


def test_camera_and_observation_validation() -> None:
    with pytest.raises(ValueError, match="positive"):
        ImageSize(0, 480)
    with pytest.raises(ValueError, match="focal"):
        CameraIntrinsics(0.0, 1.0, 0.0, 0.0, ImageSize(10, 10))
    with pytest.raises(ValueError, match="4, 5, 8"):
        DistortionCoefficients((0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="counts"):
        CalibrationObservation(
            "bad",
            ImageSize(10, 10),
            np.zeros((4, 3)),
            np.zeros((3, 2)),
        )


def test_checkerboard_is_extracted_from_generic_image_frame() -> None:
    square_px = 50
    columns, rows = 10, 7
    image = np.full((rows * square_px + 60, columns * square_px + 60), 255, dtype=np.uint8)
    for row in range(rows):
        for column in range(columns):
            if (row + column) % 2 == 0:
                image[
                    30 + row * square_px : 30 + (row + 1) * square_px,
                    30 + column * square_px : 30 + (column + 1) * square_px,
                ] = 0
    frame = ImageFrame(FrameId("camera"), datetime(2026, 8, 23, tzinfo=UTC), image, "board")
    result = extract_checkerboard_observations((frame,), CheckerboardSpec(9, 6, 0.025))
    assert len(result.observations) == 1
    assert result.rejected_source_ids == ()
    assert result.observations[0].image_points_px.shape == (54, 2)
