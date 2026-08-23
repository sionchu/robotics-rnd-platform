"""Robot operation results independent of vendor status objects."""

from __future__ import annotations

from dataclasses import dataclass

from .models import RobotState


@dataclass(frozen=True, slots=True)
class RobotResult:
    success: bool
    message: str
    state: RobotState
    command_id: str | None = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("robot result message is required")
