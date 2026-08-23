"""Platform-owned SI/geometry mapping for Rainbow's documented wire conventions."""

from __future__ import annotations

from math import asin, atan2, cos, degrees, pi, radians, sin, sqrt

import numpy as np

from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Pose, Quaternion, Vector3


def radians_to_degrees(values: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(degrees(value) for value in values)


def degrees_to_radians(values: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(radians(value) for value in values)


def _quaternion_from_rotation_matrix(matrix: np.ndarray) -> Quaternion:
    trace = float(np.trace(matrix))
    if trace > 0.0:
        scale = sqrt(trace + 1.0) * 2.0
        return Quaternion(
            (matrix[2, 1] - matrix[1, 2]) / scale,
            (matrix[0, 2] - matrix[2, 0]) / scale,
            (matrix[1, 0] - matrix[0, 1]) / scale,
            0.25 * scale,
        )
    index = int(np.argmax(np.diag(matrix)))
    if index == 0:
        scale = sqrt(1.0 + matrix[0, 0] - matrix[1, 1] - matrix[2, 2]) * 2.0
        return Quaternion(
            0.25 * scale,
            (matrix[0, 1] + matrix[1, 0]) / scale,
            (matrix[0, 2] + matrix[2, 0]) / scale,
            (matrix[2, 1] - matrix[1, 2]) / scale,
        )
    if index == 1:
        scale = sqrt(1.0 + matrix[1, 1] - matrix[0, 0] - matrix[2, 2]) * 2.0
        return Quaternion(
            (matrix[0, 1] + matrix[1, 0]) / scale,
            0.25 * scale,
            (matrix[1, 2] + matrix[2, 1]) / scale,
            (matrix[0, 2] - matrix[2, 0]) / scale,
        )
    scale = sqrt(1.0 + matrix[2, 2] - matrix[0, 0] - matrix[1, 1]) * 2.0
    return Quaternion(
        (matrix[0, 2] + matrix[2, 0]) / scale,
        (matrix[1, 2] + matrix[2, 1]) / scale,
        0.25 * scale,
        (matrix[1, 0] - matrix[0, 1]) / scale,
    )


def euler_xyz_zyx_degrees_to_quaternion(rx_deg: float, ry_deg: float, rz_deg: float) -> Quaternion:
    """Map stored XYZ angles using the documented `Rz @ Ry @ Rx` convention."""

    rx, ry, rz = radians(rx_deg), radians(ry_deg), radians(rz_deg)
    rotation_x = np.array(((1.0, 0.0, 0.0), (0.0, cos(rx), -sin(rx)), (0.0, sin(rx), cos(rx))))
    rotation_y = np.array(((cos(ry), 0.0, sin(ry)), (0.0, 1.0, 0.0), (-sin(ry), 0.0, cos(ry))))
    rotation_z = np.array(((cos(rz), -sin(rz), 0.0), (sin(rz), cos(rz), 0.0), (0.0, 0.0, 1.0)))
    return _quaternion_from_rotation_matrix(rotation_z @ rotation_y @ rotation_x)


def quaternion_to_euler_xyz_zyx_degrees(quaternion: Quaternion) -> tuple[float, float, float]:
    matrix = quaternion.as_rotation_matrix()
    clamped = min(1.0, max(-1.0, -float(matrix[2, 0])))
    ry = asin(clamped)
    # Floating-point quaternion reconstruction can leave |cos(ry)| around
    # 1e-8 at exact gimbal lock, so use a conservative decomposition branch.
    if abs(cos(ry)) > 1e-7:
        rx = atan2(float(matrix[2, 1]), float(matrix[2, 2]))
        rz = atan2(float(matrix[1, 0]), float(matrix[0, 0]))
    else:
        ry = pi / 2.0 if ry >= 0.0 else -pi / 2.0
        rx = 0.0
        rz = atan2(-float(matrix[0, 1]), float(matrix[1, 1]))
    result = tuple(degrees(value) for value in (rx, ry, rz))
    return (
        0.0 if abs(result[0]) < 1e-12 else result[0],
        0.0 if abs(result[1]) < 1e-12 else result[1],
        0.0 if abs(result[2]) < 1e-12 else result[2],
    )


def vendor_pose_to_platform(
    pose_mm_deg: tuple[float, float, float, float, float, float], frame: FrameId
) -> Pose:
    x_mm, y_mm, z_mm, rx_deg, ry_deg, rz_deg = pose_mm_deg
    return Pose(
        Vector3(x_mm / 1000.0, y_mm / 1000.0, z_mm / 1000.0),
        euler_xyz_zyx_degrees_to_quaternion(rx_deg, ry_deg, rz_deg),
        frame,
    )


def platform_pose_to_vendor(
    pose: Pose, expected_frame: FrameId
) -> tuple[float, float, float, float, float, float]:
    if pose.frame != expected_frame:
        raise ValueError(f"Rainbow pose must be in {expected_frame}, got {pose.frame}")
    rx_deg, ry_deg, rz_deg = quaternion_to_euler_xyz_zyx_degrees(pose.orientation)
    return (
        pose.position_m.x * 1000.0,
        pose.position_m.y * 1000.0,
        pose.position_m.z * 1000.0,
        rx_deg,
        ry_deg,
        rz_deg,
    )


def equivalent_euler_rotation(
    first_deg: tuple[float, float, float], second_deg: tuple[float, float, float], tolerance: float = 1e-9
) -> bool:
    first = euler_xyz_zyx_degrees_to_quaternion(*first_deg).as_rotation_matrix()
    second = euler_xyz_zyx_degrees_to_quaternion(*second_deg).as_rotation_matrix()
    return bool(np.allclose(first, second, atol=tolerance, rtol=0.0))


TAU_DEGREES = degrees(2.0 * pi)
