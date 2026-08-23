from __future__ import annotations

from datetime import UTC, datetime

import pytest

from robotics_rnd.core import FrameId, QualityMetric
from robotics_rnd.core.geometry import Pose, Quaternion, Vector3
from robotics_rnd.vision import VisionObservation, VisionTarget


@pytest.fixture
def camera_frame() -> FrameId:
    return FrameId("camera")


@pytest.fixture
def base_frame() -> FrameId:
    return FrameId("robot_base")


@pytest.fixture
def observation(camera_frame: FrameId) -> VisionObservation:
    target = VisionTarget(
        "target-1",
        Pose(Vector3(0.1, 0.2, 0.3), Quaternion.identity(), camera_frame),
        confidence=0.9,
        quality=(QualityMetric("fit", 0.9),),
    )
    return VisionObservation(
        "observation-1",
        datetime(2026, 1, 1, tzinfo=UTC),
        camera_frame,
        targets=(target,),
        metadata={"fixture": "generic"},
    )
