"""Generic robot commands. Adapters translate them into vendor calls."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from robotics_rnd.core.geometry import Pose


class CommandKind(StrEnum):
    MOVE_JOINT = "MOVE_JOINT"
    MOVE_LINEAR = "MOVE_LINEAR"
    STOP = "STOP"


@dataclass(frozen=True, slots=True)
class RobotCommand:
    kind: CommandKind
    joint_positions_rad: tuple[float, ...] | None = None
    target_pose: Pose | None = None

    def __post_init__(self) -> None:
        if self.kind is CommandKind.MOVE_JOINT:
            if not self.joint_positions_rad or self.target_pose is not None:
                raise ValueError("MOVE_JOINT requires only joint_positions_rad")
            if not all(isfinite(value) for value in self.joint_positions_rad):
                raise ValueError("joint command values must be finite radians")
        elif self.kind is CommandKind.MOVE_LINEAR:
            if self.target_pose is None or self.joint_positions_rad is not None:
                raise ValueError("MOVE_LINEAR requires only target_pose")
        elif self.kind is CommandKind.STOP:
            if self.target_pose is not None or self.joint_positions_rad is not None:
                raise ValueError("STOP does not accept a target")

    @classmethod
    def move_joint(cls, positions_rad: tuple[float, ...]) -> RobotCommand:
        return cls(CommandKind.MOVE_JOINT, joint_positions_rad=positions_rad)

    @classmethod
    def move_linear(cls, target_pose: Pose) -> RobotCommand:
        return cls(CommandKind.MOVE_LINEAR, target_pose=target_pose)

    @classmethod
    def stop(cls) -> RobotCommand:
        return cls(CommandKind.STOP)
