import math

import numpy as np
import pytest

from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Quaternion, Transform, Vector3


def quaternion_axis_angle(axis: np.ndarray, angle_rad: float) -> Quaternion:
    normalized = axis / np.linalg.norm(axis)
    sine = math.sin(angle_rad / 2.0)
    return Quaternion(
        float(normalized[0] * sine),
        float(normalized[1] * sine),
        float(normalized[2] * sine),
        math.cos(angle_rad / 2.0),
    )


def test_base_camera_times_camera_tag_is_base_tag() -> None:
    base, camera, tag = FrameId("base"), FrameId("camera"), FrameId("tag")
    t_base_camera = Transform(
        base,
        camera,
        Vector3(0.4, -0.1, 0.7),
        quaternion_axis_angle(np.array([0.0, 0.0, 1.0]), math.radians(25.0)),
    )
    t_camera_tag = Transform(
        camera,
        tag,
        Vector3(0.05, 0.02, 0.8),
        quaternion_axis_angle(np.array([1.0, 0.0, 0.0]), math.radians(175.0)),
    )

    t_base_tag = t_base_camera @ t_camera_tag
    expected_matrix = t_base_camera.as_matrix() @ t_camera_tag.as_matrix()
    assert t_base_tag.name == "T_base_tag"
    assert np.allclose(t_base_tag.as_matrix(), expected_matrix, atol=1.0e-12)
    assert np.allclose((t_base_tag @ t_base_tag.inverse()).as_matrix(), np.eye(4), atol=1.0e-12)
    with pytest.raises(ValueError, match="cannot compose"):
        t_camera_tag @ t_base_camera


def test_deterministic_random_transform_chains_round_trip() -> None:
    rng = np.random.default_rng(20260823)
    base, camera, tag = FrameId("base"), FrameId("camera"), FrameId("tag")
    for _ in range(50):
        first_axis = rng.normal(size=3)
        second_axis = rng.normal(size=3)
        t_base_camera = Transform(
            base,
            camera,
            Vector3.from_iterable(rng.uniform(-1.0, 1.0, size=3)),
            quaternion_axis_angle(first_axis, float(rng.uniform(-math.pi, math.pi))),
        )
        t_camera_tag = Transform(
            camera,
            tag,
            Vector3.from_iterable(rng.uniform(-1.0, 1.0, size=3)),
            quaternion_axis_angle(second_axis, float(rng.uniform(-math.pi, math.pi))),
        )
        composed = t_base_camera @ t_camera_tag
        recovered = t_base_camera.inverse() @ composed
        assert np.allclose(recovered.as_matrix(), t_camera_tag.as_matrix(), atol=1.0e-12)
