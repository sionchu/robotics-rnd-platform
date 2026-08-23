import math
from datetime import UTC, datetime

import numpy as np
import pytest

from robotics_rnd.core import FrameId
from robotics_rnd.vision.camera import (
    CameraIntrinsics,
    CameraModel,
    DistortionCoefficients,
    ImageFrame,
    ImageSequenceSource,
    ImageSize,
)
from robotics_rnd.vision.camera.synthetic import render_apriltag_frame
from robotics_rnd.vision.detection import AprilTagObservation, OpenCvAprilTagDetector


def camera_model() -> CameraModel:
    size = ImageSize(640, 480)
    return CameraModel(
        CameraIntrinsics(600.0, 600.0, 320.0, 240.0, size),
        DistortionCoefficients(),
        FrameId("camera"),
    )


def test_deterministic_synthetic_apriltag_detection_and_ordering() -> None:
    camera = camera_model()
    options = {
        "tag_id": 7,
        "tag_size_m": 0.12,
        "rvec_tag_to_camera": np.array([math.pi - 0.2, 0.12, 0.08]),
        "tvec_tag_to_camera_m": np.array([0.03, -0.02, 0.8]),
        "image_noise_std": 1.5,
        "seed": 17,
    }
    first = render_apriltag_frame(camera, **options)
    second = render_apriltag_frame(camera, **options)
    assert np.array_equal(first.image, second.image)

    detections = OpenCvAprilTagDetector("tag36h11").detect(first)
    assert len(detections) == 1
    detection = detections[0]
    assert detection.tag_id == 7
    assert detection.tag_family == "tag36h11"
    assert detection.area_px2 > 1_000.0
    assert detection.center_pixel[0] > camera.image_size.width_px / 2
    top_left, top_right, bottom_right, bottom_left = detection.corner_pixels
    assert top_left[1] < bottom_left[1]
    assert top_right[1] < bottom_right[1]


def test_no_tag_and_replay_exhaustion() -> None:
    camera = camera_model()
    blank = ImageFrame(
        camera.frame_id,
        datetime(2026, 8, 23, tzinfo=UTC),
        np.full(camera.image_size.shape, 255, dtype=np.uint8),
        "blank",
    )
    assert OpenCvAprilTagDetector().detect(blank) == ()
    replay = ImageSequenceSource((blank,))
    assert replay.read().source_id == "blank"
    assert replay.remaining == 0
    with pytest.raises(StopIteration):
        replay.read()
    replay.reset()
    assert replay.remaining == 1


def test_apriltag_model_and_family_validation() -> None:
    size = ImageSize(100, 100)
    with pytest.raises(ValueError, match="clockwise"):
        AprilTagObservation(
            "tag36h11",
            1,
            ((10.0, 10.0), (10.0, 20.0), (20.0, 20.0), (20.0, 10.0)),
            datetime(2026, 8, 23, tzinfo=UTC),
            FrameId("camera"),
            size,
        )
    with pytest.raises(ValueError, match="unsupported"):
        OpenCvAprilTagDetector("unknown")
