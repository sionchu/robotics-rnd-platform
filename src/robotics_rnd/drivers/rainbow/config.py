"""Explicitly safe configuration for the Rainbow adapter boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class RainbowOperationMode(StrEnum):
    READ_ONLY = "READ_ONLY"
    FAKE = "FAKE"
    LIVE_MANUAL = "LIVE_MANUAL"


@dataclass(frozen=True, slots=True)
class RainbowConfig:
    operation_mode: RainbowOperationMode = RainbowOperationMode.READ_ONLY
    host: str | None = None
    command_port: int = 5000
    data_port: int = 5001
    connect_timeout_s: float = 3.0
    command_timeout_s: float = 5.0
    state_timeout_s: float = 1.0
    stale_state_after_s: float = 1.0
    motion_enabled: bool = False
    io_write_enabled: bool = False
    auto_reconnect: bool = False
    base_frame: str = "robot_base"
    expected_joint_count: int = 6

    def __post_init__(self) -> None:
        if self.operation_mode is RainbowOperationMode.LIVE_MANUAL and not self.host:
            raise ValueError("LIVE_MANUAL mode requires an explicit controller host")
        if self.operation_mode is RainbowOperationMode.READ_ONLY and self.motion_enabled:
            raise ValueError("READ_ONLY mode cannot enable motion")
        if self.auto_reconnect:
            raise ValueError("automatic reconnect is disabled; state must be reviewed after reconnect")
        for name, value in (
            ("connect_timeout_s", self.connect_timeout_s),
            ("command_timeout_s", self.command_timeout_s),
            ("state_timeout_s", self.state_timeout_s),
            ("stale_state_after_s", self.stale_state_after_s),
        ):
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a positive finite value")
        if not 1 <= self.command_port <= 65535 or not 1 <= self.data_port <= 65535:
            raise ValueError("Rainbow ports must be between 1 and 65535")
        if self.expected_joint_count <= 0:
            raise ValueError("expected_joint_count must be positive")
        if not self.base_frame.strip():
            raise ValueError("base_frame is required")
