"""Robot state values with explicit radian and meter conventions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Any

from robotics_rnd.core.geometry import Pose


def _now() -> datetime:
    return datetime.now(UTC)


class RobotMode(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    IDLE = "IDLE"
    MOVING = "MOVING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    FAULT = "FAULT"
    UNKNOWN = "UNKNOWN"


class ConnectionState(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    RECONNECTING = "RECONNECTING"
    FAULTED = "FAULTED"
    SHUTTING_DOWN = "SHUTTING_DOWN"


class FaultCategory(StrEnum):
    COMMUNICATION = "COMMUNICATION"
    CONNECTION = "CONNECTION"
    COMMAND_REJECTED = "COMMAND_REJECTED"
    COMMAND_TIMEOUT = "COMMAND_TIMEOUT"
    CONTROLLER = "CONTROLLER"
    MOTION = "MOTION"
    SAFETY = "SAFETY"
    IO = "IO"
    CONFIGURATION = "CONFIGURATION"
    APPLICATION = "APPLICATION"
    STALE_STATE = "STALE_STATE"
    VALIDATION = "VALIDATION"
    UNKNOWN = "UNKNOWN"


class FaultSeverity(StrEnum):
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class RobotFaultRecord:
    category: FaultCategory
    severity: FaultSeverity
    code: str
    message: str
    occurred_at: datetime = field(default_factory=_now)
    recoverable: bool = False
    source: str = "platform"
    raw_vendor_context: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError("fault code and message are required")
        if self.occurred_at.tzinfo is None:
            raise ValueError("fault occurrence time must be timezone-aware")
        if not self.source.strip():
            raise ValueError("fault source is required")
        if self.raw_vendor_context is None:
            object.__setattr__(self, "raw_vendor_context", MappingProxyType({}))
        else:
            object.__setattr__(
                self,
                "raw_vendor_context",
                MappingProxyType(dict(self.raw_vendor_context)),
            )


@dataclass(frozen=True, slots=True)
class RobotMetadata:
    manufacturer: str
    model: str
    adapter: str
    adapter_version: str
    controller_version: str | None = None

    def __post_init__(self) -> None:
        for value in (self.manufacturer, self.model, self.adapter, self.adapter_version):
            if not value.strip():
                raise ValueError("robot metadata fields must be non-empty")


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
    connection_state: ConnectionState | None = None
    source_timestamp: datetime | None = None
    task_state: int | str | None = None
    speed_ratio: float | None = None
    digital_inputs: tuple[bool, ...] = ()
    digital_outputs: tuple[bool, ...] = ()
    fault: RobotFaultRecord | None = None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("robot timestamp must be timezone-aware")
        if self.source_timestamp is not None and self.source_timestamp.tzinfo is None:
            raise ValueError("robot source timestamp must be timezone-aware")
        if not self.connected and self.mode is not RobotMode.DISCONNECTED:
            raise ValueError("a disconnected robot must use DISCONNECTED mode")
        if self.mode is RobotMode.FAULT and not self.fault_message:
            raise ValueError("FAULT mode requires a fault message")
        if self.speed_ratio is not None and (
            not isfinite(self.speed_ratio) or not 0.0 <= self.speed_ratio <= 1.0
        ):
            raise ValueError("speed ratio must be finite and between zero and one")
        inferred = ConnectionState.CONNECTED if self.connected else ConnectionState.DISCONNECTED
        if self.connection_state is None:
            object.__setattr__(self, "connection_state", inferred)
        elif self.connected and self.connection_state is ConnectionState.DISCONNECTED:
            raise ValueError("connected state cannot use a disconnected connection state")
        elif not self.connected and self.connection_state is ConnectionState.CONNECTED:
            raise ValueError("disconnected state cannot use a connected connection state")
        if self.fault is not None and self.fault_message is None:
            object.__setattr__(self, "fault_message", self.fault.message)
