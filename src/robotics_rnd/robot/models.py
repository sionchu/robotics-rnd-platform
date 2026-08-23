"""Robot state values with explicit radian and meter conventions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite

from robotics_rnd.core.geometry import Pose


def _now() -> datetime:
    return datetime.now(UTC)


class RobotMode(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    IDLE = "IDLE"
    MOVING = "MOVING"
    STOPPED = "STOPPED"
    FAULT = "FAULT"


@dataclass(frozen=True, slots=True)
class JointState:
    """Named joint positions and optional velocities, all in radians."""

    names: tuple[str, ...]
    positions_rad: tuple[float, ...]
    velocities_rad_s: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if not self.names or len(self.names) != len(self.positions_rad):
            raise ValueError("joint names and positions must be non-empty and have equal length")
        if len(set(self.names)) != len(self.names) or any(not name.strip() for name in self.names):
            raise ValueError("joint names must be non-empty and unique")
        if not all(isfinite(value) for value in self.positions_rad):
            raise ValueError("joint positions must be finite radians")
        if self.velocities_rad_s is not None:
            if len(self.velocities_rad_s) != len(self.names):
                raise ValueError("joint velocity count must match joint names")
            if not all(isfinite(value) for value in self.velocities_rad_s):
                raise ValueError("joint velocities must be finite radians/second")


@dataclass(frozen=True, slots=True)
class RobotState:
    connected: bool
    mode: RobotMode
    joints: JointState
    tool_pose: Pose
    timestamp: datetime = field(default_factory=_now)
    fault_message: str | None = None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("robot timestamp must be timezone-aware")
        if not self.connected and self.mode is not RobotMode.DISCONNECTED:
            raise ValueError("a disconnected robot must use DISCONNECTED mode")
        if self.mode is RobotMode.FAULT and not self.fault_message:
            raise ValueError("FAULT mode requires a fault message")
