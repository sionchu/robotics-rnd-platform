from datetime import datetime

import pytest

from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Pose
from robotics_rnd.drivers.mock import MockVision
from robotics_rnd.drivers.replay import ReplayVision
from robotics_rnd.vision import VisionObservation, VisionTarget


def test_mock_result_is_deterministic_and_preserves_frame(observation: VisionObservation) -> None:
    provider = MockVision((observation,))
    first = provider.observe()
    second = provider.observe()
    assert first is observation
    assert second is observation
    assert first.targets[0].pose.frame == first.frame_id
    assert first.metadata["fixture"] == "generic"


def test_replay_order_exhaustion_and_reset(observation: VisionObservation) -> None:
    second = VisionObservation(
        "observation-2",
        observation.timestamp,
        observation.frame_id,
        metadata={"sequence": 2},
    )
    replay = ReplayVision((observation, second))
    assert replay.observe().observation_id == "observation-1"
    assert replay.observe().observation_id == "observation-2"
    assert replay.remaining == 0
    with pytest.raises(StopIteration):
        replay.observe()
    replay.reset()
    assert replay.observe().observation_id == "observation-1"


def test_invalid_vision_data_is_rejected() -> None:
    camera = FrameId("camera")
    with pytest.raises(ValueError, match="timezone-aware"):
        VisionObservation("obs", datetime(2026, 1, 1), camera)
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        VisionTarget("target", Pose.identity(camera), 1.1)
    with pytest.raises(ValueError, match="observation frame"):
        VisionObservation(
            "obs",
            datetime.now().astimezone(),
            camera,
            targets=(VisionTarget("target", Pose.identity(FrameId("other")), 0.5),),
        )
    with pytest.raises(ValueError, match="at least one"):
        ReplayVision(())
