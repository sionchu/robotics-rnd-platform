"""Small rigid-body primitives with explicit meter and XYZW conventions."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite, sqrt

import numpy as np

from robotics_rnd.core.frames import FrameId


def _three(values: Iterable[float], name: str) -> tuple[float, float, float]:
    result = tuple(float(value) for value in values)
    if len(result) != 3:
        raise ValueError(f"{name} must contain exactly three values")
    if not all(isfinite(value) for value in result):
        raise ValueError(f"{name} values must be finite")
    return result


@dataclass(frozen=True, slots=True)
class Vector3:
    """A finite three-vector; position/translation uses meters by convention."""

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        values = (float(self.x), float(self.y), float(self.z))
        if not all(isfinite(value) for value in values):
            raise ValueError("vector values must be finite")
        object.__setattr__(self, "x", values[0])
        object.__setattr__(self, "y", values[1])
        object.__setattr__(self, "z", values[2])

    @classmethod
    def from_iterable(cls, values: Iterable[float]) -> Vector3:
        return cls(*_three(values, "vector"))

    @classmethod
    def zero(cls) -> Vector3:
        return cls(0.0, 0.0, 0.0)

    def as_array(self) -> np.ndarray:
        return np.array((self.x, self.y, self.z), dtype=float)

    def __add__(self, other: Vector3) -> Vector3:
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3) -> Vector3:
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def scaled(self, factor: float) -> Vector3:
        if not isfinite(factor):
            raise ValueError("scale factor must be finite")
        return Vector3(self.x * factor, self.y * factor, self.z * factor)


@dataclass(frozen=True, slots=True)
class Quaternion:
    """Normalized quaternion in public `(x, y, z, w)` order."""

    x: float
    y: float
    z: float
    w: float

    def __post_init__(self) -> None:
        values = tuple(float(value) for value in (self.x, self.y, self.z, self.w))
        if not all(isfinite(value) for value in values):
            raise ValueError("quaternion values must be finite")
        norm = sqrt(sum(value * value for value in values))
        if norm <= np.finfo(float).eps:
            raise ValueError("quaternion norm must be non-zero")
        normalized = tuple(value / norm for value in values)
        object.__setattr__(self, "x", normalized[0])
        object.__setattr__(self, "y", normalized[1])
        object.__setattr__(self, "z", normalized[2])
        object.__setattr__(self, "w", normalized[3])

    @classmethod
    def identity(cls) -> Quaternion:
        return cls(0.0, 0.0, 0.0, 1.0)

    def conjugate(self) -> Quaternion:
        return Quaternion(-self.x, -self.y, -self.z, self.w)

    def __matmul__(self, other: Quaternion) -> Quaternion:
        x1, y1, z1, w1 = self.x, self.y, self.z, self.w
        x2, y2, z2, w2 = other.x, other.y, other.z, other.w
        return Quaternion(
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        )

    def as_rotation_matrix(self) -> np.ndarray:
        x, y, z, w = self.x, self.y, self.z, self.w
        return np.array(
            [
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
            ],
            dtype=float,
        )

    def rotate(self, vector: Vector3) -> Vector3:
        return Vector3.from_iterable(self.as_rotation_matrix() @ vector.as_array())


@dataclass(frozen=True, slots=True)
class Point3:
    """A position in meters, expressed in one explicit coordinate frame."""

    position_m: Vector3
    frame: FrameId


@dataclass(frozen=True, slots=True)
class Pose:
    """A body pose in meters with an XYZW quaternion and explicit parent frame."""

    position_m: Vector3
    orientation: Quaternion
    frame: FrameId

    @classmethod
    def identity(cls, frame: FrameId) -> Pose:
        return cls(Vector3.zero(), Quaternion.identity(), frame)


@dataclass(frozen=True, slots=True)
class Transform:
    """`T_target_source`: maps source-frame coordinates into target-frame coordinates."""

    target_frame: FrameId
    source_frame: FrameId
    translation_m: Vector3
    rotation: Quaternion

    @property
    def name(self) -> str:
        return f"T_{self.target_frame}_{self.source_frame}"

    @classmethod
    def identity(cls, frame: FrameId) -> Transform:
        return cls(frame, frame, Vector3.zero(), Quaternion.identity())

    def as_matrix(self) -> np.ndarray:
        matrix = np.eye(4, dtype=float)
        matrix[:3, :3] = self.rotation.as_rotation_matrix()
        matrix[:3, 3] = self.translation_m.as_array()
        return matrix

    def inverse(self) -> Transform:
        inverse_rotation = self.rotation.conjugate()
        inverse_translation = inverse_rotation.rotate(self.translation_m).scaled(-1.0)
        return Transform(self.source_frame, self.target_frame, inverse_translation, inverse_rotation)

    def compose(self, other: Transform) -> Transform:
        """Return `self @ other`, applying `other` and then `self`."""

        if self.source_frame != other.target_frame:
            raise ValueError(
                f"frame mismatch: {self.name} cannot compose with {other.name}; "
                f"{self.source_frame!s} != {other.target_frame!s}"
            )
        translation = self.rotation.rotate(other.translation_m) + self.translation_m
        return Transform(
            self.target_frame,
            other.source_frame,
            translation,
            self.rotation @ other.rotation,
        )

    def __matmul__(self, other: Transform) -> Transform:
        return self.compose(other)

    def transform_point(self, point: Point3) -> Point3:
        if point.frame != self.source_frame:
            raise ValueError(f"point is in {point.frame}, expected {self.source_frame}")
        position = self.rotation.rotate(point.position_m) + self.translation_m
        return Point3(position, self.target_frame)

    def transform_pose(self, pose: Pose) -> Pose:
        if pose.frame != self.source_frame:
            raise ValueError(f"pose is in {pose.frame}, expected {self.source_frame}")
        position = self.rotation.rotate(pose.position_m) + self.translation_m
        return Pose(position, self.rotation @ pose.orientation, self.target_frame)
