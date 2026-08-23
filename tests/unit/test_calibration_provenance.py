from __future__ import annotations

from pathlib import Path

import pytest

from robotics_rnd.vision.calibration import (
    CalibrationArtifact,
    CameraCalibrationResult,
    CameraConfigurationBinding,
    ReprojectionMetrics,
    load_calibration_artifact,
    save_calibration_artifact,
)
from robotics_rnd.vision.camera import CameraIntrinsics, DistortionCoefficients, ImageSize
from robotics_rnd.vision.dataset import GroundTruthClass


def artifact() -> CalibrationArtifact:
    size = ImageSize(1280, 720)
    calibration = CameraCalibrationResult(
        intrinsics=CameraIntrinsics(900.0, 900.0, 640.0, 360.0, size),
        distortion=DistortionCoefficients(),
        metrics=ReprojectionMetrics(0.2, 0.15, 0.5, (0.2,) * 8),
        method="test",
        target="checkerboard",
        accepted_observations=8,
    )
    return CalibrationArtifact(
        calibration=calibration,
        binding=CameraConfigurationBinding(
            sensor_model="detected-sensor",
            camera_mode="detected-mode",
            capture_size=size,
            calibration_size=size,
            pixel_format="BGR888",
        ),
        dataset_id="calibration-session",
        ground_truth_class=GroundTruthClass.MEASURED_PHYSICAL_REFERENCE,
        measurement_uncertainty="square size measured to stated manual uncertainty",
        software_versions={"opencv": "4.x"},
    )


def test_calibration_artifact_round_trip_and_binding(tmp_path: Path) -> None:
    expected = artifact()
    path = tmp_path / "artifact.json"
    save_calibration_artifact(expected, path)
    loaded = load_calibration_artifact(path)
    assert loaded == expected
    loaded.binding.assert_compatible(
        sensor_model="detected-sensor",
        camera_mode="detected-mode",
        capture_size=ImageSize(1280, 720),
        pixel_format="BGR888",
    )
    with pytest.raises(ValueError, match="does not match"):
        loaded.binding.assert_compatible(
            sensor_model="detected-sensor",
            camera_mode="other-mode",
            capture_size=ImageSize(1280, 720),
            pixel_format="BGR888",
        )


def test_intrinsic_scaling_requires_preserved_aspect_ratio() -> None:
    intrinsics = CameraIntrinsics(900.0, 800.0, 640.0, 360.0, ImageSize(1280, 720))
    scaled = intrinsics.scaled_to(ImageSize(640, 360))
    assert scaled == CameraIntrinsics(450.0, 400.0, 320.0, 180.0, ImageSize(640, 360))
    with pytest.raises(ValueError, match="aspect ratio"):
        intrinsics.scaled_to(ImageSize(640, 480))
