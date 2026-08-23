"""Robot operation results independent of vendor status objects."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from .models import RobotState


def _now() -> datetime:
    return datetime.now(UTC)


class CommandStatus(StrEnum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    STOPPED = "STOPPED"
    UNKNOWN = "UNKNOWN"


class StatusEvidence(StrEnum):
    VENDOR_REPORTED = "VENDOR_REPORTED"
    ADAPTER_DERIVED = "ADAPTER_DERIVED"
    APPLICATION_DERIVED = "APPLICATION_DERIVED"


_ALLOWED_TRANSITIONS: dict[CommandStatus, frozenset[CommandStatus]] = {
    CommandStatus.CREATED: frozenset({CommandStatus.VALIDATED, CommandStatus.CANCELLED}),
    CommandStatus.VALIDATED: frozenset({CommandStatus.SUBMITTED, CommandStatus.FAILED}),
    CommandStatus.SUBMITTED: frozenset(
        {CommandStatus.ACCEPTED, CommandStatus.FAILED, CommandStatus.TIMED_OUT, CommandStatus.UNKNOWN}
    ),
    CommandStatus.ACCEPTED: frozenset(
        {
            CommandStatus.RUNNING,
            CommandStatus.COMPLETED,
            CommandStatus.FAILED,
            CommandStatus.TIMED_OUT,
            CommandStatus.STOPPED,
            CommandStatus.UNKNOWN,
        }
    ),
    CommandStatus.RUNNING: frozenset(
        {
            CommandStatus.COMPLETED,
            CommandStatus.FAILED,
            CommandStatus.TIMED_OUT,
            CommandStatus.STOPPED,
            CommandStatus.UNKNOWN,
        }
    ),
    CommandStatus.UNKNOWN: frozenset(),
    CommandStatus.COMPLETED: frozenset(),
    CommandStatus.FAILED: frozenset(),
    CommandStatus.TIMED_OUT: frozenset(),
    CommandStatus.CANCELLED: frozenset(),
    CommandStatus.STOPPED: frozenset(),
}


def validate_command_transition(previous: CommandStatus, current: CommandStatus) -> None:
    if current not in _ALLOWED_TRANSITIONS[previous]:
        raise ValueError(f"invalid command transition: {previous.value} -> {current.value}")


@dataclass(frozen=True, slots=True)
class CommandLifecycleEvent:
    command_id: str
    status: CommandStatus
    evidence: StatusEvidence
    timestamp: datetime = field(default_factory=_now)
    message: str = ""

    def __post_init__(self) -> None:
        if not self.command_id.strip():
            raise ValueError("lifecycle event command_id is required")
        if self.timestamp.tzinfo is None:
            raise ValueError("lifecycle event timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class RobotResult:
    success: bool
    message: str
    state: RobotState
    command_id: str | None = None
    status: CommandStatus | None = None
    status_evidence: StatusEvidence = StatusEvidence.ADAPTER_DERIVED
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    diagnostics: Mapping[str, Any] | None = None
    vendor_code: str | None = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("robot result message is required")
        if self.status is None:
            object.__setattr__(
                self,
                "status",
                CommandStatus.COMPLETED if self.success else CommandStatus.FAILED,
            )
        if self.success and self.status in {
            CommandStatus.FAILED,
            CommandStatus.TIMED_OUT,
            CommandStatus.UNKNOWN,
        }:
            raise ValueError("successful result cannot use a failure or unknown status")
        for timestamp in (self.started_at, self.completed_at):
            if timestamp is not None and timestamp.tzinfo is None:
                raise ValueError("result timestamps must be timezone-aware")
        if self.diagnostics is None:
            object.__setattr__(self, "diagnostics", MappingProxyType({}))
        else:
            object.__setattr__(self, "diagnostics", MappingProxyType(dict(self.diagnostics)))

    @property
    def duration_s(self) -> float | None:
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()
