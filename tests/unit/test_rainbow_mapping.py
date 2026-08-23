from math import pi

import numpy as np
import pytest

from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Pose, Quaternion, Vector3
from robotics_rnd.drivers.rainbow.mapping import (
    degrees_to_radians,
    equivalent_euler_rotation,
    platform_pose_to_vendor,
    quaternion_to_euler_xyz_zyx_degrees,
    radians_to_degrees,
    vendor_pose_to_platform,
)


def test_joint_angle_units_round_trip() -> None:
    values = (0.0, pi / 2, -pi, 0.1, -0.2, 0.3)
    assert degrees_to_radians(radians_to_degrees(values)) == pytest.approx(values)


@pytest.mark.parametrize(
    "angles",
    [
        (0.0, 0.0, 0.0),
        (10.0, 20.0, 30.0),
        (-170.0, 45.0, 179.0),
        (45.0, 89.999, -30.0),
        (20.0, 90.0, 40.0),
        (-20.0, -90.0, 40.0),
    ],
)
def test_documented_zyx_rotation_mapping_round_trips_as_rotation(
    angles: tuple[float, float, float],
) -> None:
    pose = vendor_pose_to_platform((100.0, -200.0, 300.0, *angles), FrameId("robot_base"))
    mapped = platform_pose_to_vendor(pose, FrameId("robot_base"))
    assert mapped[:3] == pytest.approx((100.0, -200.0, 300.0))
    assert equivalent_euler_rotation(angles, mapped[3:], tolerance=1e-8)


def test_linear_pose_mapping_uses_meters_and_explicit_frame() -> None:
    pose = Pose(Vector3(0.1, 0.2, 0.3), Quaternion.identity(), FrameId("robot_base"))
    mapped = platform_pose_to_vendor(pose, FrameId("robot_base"))
    assert mapped == pytest.approx((100.0, 200.0, 300.0, 0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="must be in"):
        platform_pose_to_vendor(pose, FrameId("camera"))


def test_quaternion_decomposition_returns_finite_values_at_gimbal_lock() -> None:
    pose = vendor_pose_to_platform((0.0, 0.0, 0.0, 20.0, 90.0, 40.0), FrameId("base"))
    values = quaternion_to_euler_xyz_zyx_degrees(pose.orientation)
    assert np.isfinite(np.asarray(values)).all()
