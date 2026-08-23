import math

import numpy as np
import pytest

from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Point3, Pose, Quaternion, Transform, Vector3


def quaternion_z(degrees: float) -> Quaternion:
    half = math.radians(degrees) / 2.0
    return Quaternion(0.0, 0.0, math.sin(half), math.cos(half))


def test_transform_identity_point_and_pose() -> None:
    frame = FrameId("world")
    identity = Transform.identity(frame)
    point = Point3(Vector3(1.0, -2.0, 3.0), frame)
    pose = Pose(Vector3(0.1, 0.2, 0.3), quaternion_z(30), frame)
    assert identity.transform_point(point) == point
    transformed = identity.transform_pose(pose)
    assert transformed.frame == frame
    assert np.allclose(transformed.position_m.as_array(), pose.position_m.as_array())
    assert np.allclose(identity.as_matrix(), np.eye(4))


def test_inverse_correctness_and_composition() -> None:
    base, camera, target = FrameId("base"), FrameId("camera"), FrameId("target")
    t_base_camera = Transform(base, camera, Vector3(1.0, 0.0, 0.0), quaternion_z(90))
    t_camera_target = Transform(camera, target, Vector3(0.0, 2.0, 0.0), Quaternion.identity())
    t_base_target = t_base_camera @ t_camera_target
    result = t_base_target.transform_point(Point3(Vector3.zero(), target))
    assert np.allclose(result.position_m.as_array(), [-1.0, 0.0, 0.0], atol=1e-12)
    identity = t_base_target @ t_base_target.inverse()
    assert identity.target_frame == base
    assert identity.source_frame == base
    assert np.allclose(identity.as_matrix(), np.eye(4), atol=1e-12)


def test_pose_transform_rotates_position_and_orientation() -> None:
    base, camera = FrameId("base"), FrameId("camera")
    transform = Transform(base, camera, Vector3(1.0, 0.0, 0.0), quaternion_z(90))
    pose = Pose(Vector3(1.0, 0.0, 0.0), Quaternion.identity(), camera)
    result = transform.transform_pose(pose)
    assert result.frame == base
    assert np.allclose(result.position_m.as_array(), [1.0, 1.0, 0.0], atol=1e-12)
    assert np.allclose(result.orientation.as_rotation_matrix(), quaternion_z(90).as_rotation_matrix())


def test_invalid_shapes_quaternion_and_frames_are_rejected() -> None:
    with pytest.raises(ValueError, match="exactly three"):
        Vector3.from_iterable([1.0, 2.0])
    with pytest.raises(ValueError, match="non-zero"):
        Quaternion(0.0, 0.0, 0.0, 0.0)
    with pytest.raises(ValueError, match="finite"):
        Vector3(float("nan"), 0.0, 0.0)
    with pytest.raises(ValueError, match="frame id"):
        FrameId("bad frame")


def test_frame_mismatch_is_not_guessed() -> None:
    base, camera, other = FrameId("base"), FrameId("camera"), FrameId("other")
    transform = Transform(base, camera, Vector3.zero(), Quaternion.identity())
    with pytest.raises(ValueError, match="point is in"):
        transform.transform_point(Point3(Vector3.zero(), other))
    with pytest.raises(ValueError, match="cannot compose"):
        transform @ Transform.identity(other)


def test_quaternion_public_order_is_xyzw_and_normalized() -> None:
    quaternion = Quaternion(0.0, 0.0, 2.0, 2.0)
    assert np.isclose(
        math.sqrt(sum(value**2 for value in (quaternion.x, quaternion.y, quaternion.z, quaternion.w))), 1
    )
    rotated = quaternion_z(90).rotate(Vector3(1.0, 0.0, 0.0))
    assert np.allclose(rotated.as_array(), [0.0, 1.0, 0.0], atol=1e-12)
