"""Generic robot commands. Adapters translate them into vendor calls."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Any

from robotics_rnd.core.geometry import Pose


class CommandKind(StrEnum):
    MOVE_JOINT = "MOVE_JOINT"
    MOVE_LINEAR = "MOVE_LINEAR"
    STOP = "STOP"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    WRITE_DIGITAL_OUTPUT = "WRITE_DIGITAL_OUTPUT"


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class RobotCommand:
    kind: CommandKind
    joint_positions_rad: tuple[float, ...] | None = None
    target_pose: Pose | None = None
    command_id: str | None = None
    created_at: datetime | None = None
    timeout_s: float | None = None
    joint_speed_rad_s: float | None = None
    joint_acceleration_rad_s2: float | None = None
    linear_speed_m_s: float | None = None
    linear_acceleration_m_s2: float | None = None
    digital_channel: int | None = None
    digital_value: bool | None = None
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.command_id is not None and not self.command_id.strip():
            raise ValueError("command_id must be non-empty when provided")
        if self.created_at is not None and self.created_at.tzinfo is None:
            raise ValueError("command creation time must be timezone-aware")
        if self.timeout_s is not None and (not isfinite(self.timeout_s) or self.timeout_s <= 0):
            raise ValueError("command timeout must be a positive finite value")
        for name, value in (
            ("joint_speed_rad_s", self.joint_speed_rad_s),
            ("joint_acceleration_rad_s2", self.joint_acceleration_rad_s2),
            ("linear_speed_m_s", self.linear_speed_m_s),
            ("linear_acceleration_m_s2", self.linear_acceleration_m_s2),
        ):
            if value is not None and (not isfinite(value) or value <= 0):
                raise ValueError(f"{name} must be a positive finite value")
        if self.created_at is None:
            object.__setattr__(self, "created_at", _now())
        if self.metadata is None:
            object.__setattr__(self, "metadata", MappingProxyType({}))
        else:
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

        if self.kind is CommandKind.MOVE_JOINT:
            if not self.joint_positions_rad or self.target_pose is not None:
                raise ValueError("MOVE_JOINT requires only joint_positions_rad")
            if self.digital_channel is not None or self.digital_value is not None:
                raise ValueError("MOVE_JOINT does not accept digital output fields")
            if not all(isfinite(value) for value in self.joint_positions_rad):
                raise ValueError("joint command values must be finite radians")
        elif self.kind is CommandKind.MOVE_LINEAR:
            if self.target_pose is None or self.joint_positions_rad is not None:
                raise ValueError("MOVE_LINEAR requires only target_pose")
            if self.digital_channel is not None or self.digital_value is not None:
                raise ValueError("MOVE_LINEAR does not accept digital output fields")
        elif self.kind in {CommandKind.STOP, CommandKind.PAUSE, CommandKind.RESUME}:
            if self.target_pose is not None or self.joint_positions_rad is not None:
                raise ValueError(f"{self.kind.value} does not accept a target")
            if self.digital_channel is not None or self.digital_value is not None:
                raise ValueError(f"{self.kind.value} does not accept digital output fields")
        elif self.kind is CommandKind.WRITE_DIGITAL_OUTPUT:
            if self.target_pose is not None or self.joint_positions_rad is not None:
                raise ValueError("WRITE_DIGITAL_OUTPUT does not accept a motion target")
            if self.digital_channel is None or self.digital_channel < 0:
                raise ValueError("digital output channel must be a non-negative integer")
            if self.digital_value is None:
                raise ValueError("digital output value is required")

    @classmethod
    def move_joint(
        cls,
        positions_rad: tuple[float, ...],
        *,
        speed_rad_s: float | None = None,
        acceleration_rad_s2: float | None = None,
        timeout_s: float | None = None,
        command_id: str | None = None,
    ) -> RobotCommand:
        return cls(
            CommandKind.MOVE_JOINT,
            joint_positions_rad=positions_rad,
            command_id=command_id,
            timeout_s=timeout_s,
            joint_speed_rad_s=speed_rad_s,
            joint_acceleration_rad_s2=acceleration_rad_s2,
        )

    @classmethod
    def move_linear(
        cls,
        target_pose: Pose,
        *,
        speed_m_s: float | None = None,
        acceleration_m_s2: float | None = None,
        timeout_s: float | None = None,
        command_id: str | None = None,
    ) -> RobotCommand:
        return cls(
            CommandKind.MOVE_LINEAR,
            target_pose=target_pose,
            command_id=command_id,
            timeout_s=timeout_s,
            linear_speed_m_s=speed_m_s,
            linear_acceleration_m_s2=acceleration_m_s2,
        )

    @classmethod
    def stop(cls) -> RobotCommand:
        return cls(CommandKind.STOP)

    @classmethod
    def pause(cls) -> RobotCommand:
        return cls(CommandKind.PAUSE)

    @classmethod
    def resume(cls) -> RobotCommand:
        return cls(CommandKind.RESUME)

    @classmethod
    def write_digital_output(cls, channel: int, value: bool) -> RobotCommand:
        return cls(
            CommandKind.WRITE_DIGITAL_OUTPUT,
            digital_channel=channel,
            digital_value=value,
        )
