from __future__ import annotations

import os

import pytest

from robotics_rnd.drivers.raspberry_pi import PiCameraConfig, PiCameraSource
from robotics_rnd.vision.camera import ImageSize

pytestmark = pytest.mark.hardware


@pytest.mark.skipif(
    os.environ.get("ROBOTICS_RND_RUN_HARDWARE") != "1",
    reason="set ROBOTICS_RND_RUN_HARDWARE=1 only on the reviewed Pi camera node",
)
def test_live_pi_camera_captures_one_validated_frame() -> None:
    with PiCameraSource(PiCameraConfig(ImageSize(640, 480), warmup_frames=5)) as source:
        frame = source.read()
    assert frame.capture_metadata is not None
    assert frame.image_size == ImageSize(640, 480)
