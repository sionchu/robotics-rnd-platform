"""Application/HMI boundary over any platform-owned robot implementation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock

from .commands import RobotCommand
from .interface import RobotInterface
from .journal import RobotJournal
from .models import ConnectionState, RobotMode, RobotState
from .results import CommandStatus, RobotResult, StatusEvidence


class RobotApplicationState(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    READY = "READY"
    BUSY = "BUSY"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    DEGRADED = "DEGRADED"
    FAULTED = "FAULTED"


@dataclass(frozen=True, slots=True)
class RobotApplicationEvent:
    event_type: str
    state: RobotApplicationState
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    command_id: str | None = None


class RobotApplicationService:
    def __init__(self, robot: RobotInterface, journal: RobotJournal | None = None) -> None:
        self._robot = robot
        self._journal = journal
        self._listeners: list[Callable[[RobotApplicationEvent], None]] = []
        self._lock = RLock()
        self._counter = 0

    @property
    def robot(self) -> RobotInterface:
        return self._robot

    @property
    def state(self) -> RobotApplicationState:
        return self._application_state(self._robot.get_state())

    def subscribe(self, listener: Callable[[RobotApplicationEvent], None]) -> None:
        self._listeners.append(listener)

    @staticmethod
    def _application_state(state: RobotState) -> RobotApplicationState:
        if not state.connected:
            if state.connection_state in {ConnectionState.DEGRADED, ConnectionState.FAULTED}:
                return RobotApplicationState.DEGRADED
            return RobotApplicationState.DISCONNECTED
        if state.mode is RobotMode.FAULT:
            return RobotApplicationState.FAULTED
        if state.connection_state is ConnectionState.DEGRADED or state.mode is RobotMode.UNKNOWN:
            return RobotApplicationState.DEGRADED
        return {
            RobotMode.MOVING: RobotApplicationState.BUSY,
            RobotMode.PAUSED: RobotApplicationState.PAUSED,
            RobotMode.STOPPED: RobotApplicationState.STOPPED,
        }.get(state.mode, RobotApplicationState.READY)

    def _emit(self, event_type: str, result: RobotResult) -> None:
        event = RobotApplicationEvent(
            event_type,
            self._application_state(result.state),
            result.message,
            command_id=result.command_id,
        )
        if self._journal is not None:
            self._journal.append("application_event", {"event": event})
            self._journal.record_state(result.state, event_type)
        for listener in tuple(self._listeners):
            listener(event)
        if result.state.fault is not None and not result.success:
            fault_event = RobotApplicationEvent(
                "fault_raised",
                self._application_state(result.state),
                result.state.fault.message,
                command_id=result.command_id,
            )
            if self._journal is not None:
                self._journal.append("application_event", {"event": fault_event})
            for listener in tuple(self._listeners):
                listener(fault_event)

    def connect(self) -> RobotResult:
        with self._lock:
            result = self._robot.connect()
            if self._journal is not None:
                self._journal.append(
                    "session_started",
                    {
                        "adapter": type(self._robot).__name__,
                        "capabilities": sorted(capability.value for capability in self._robot.capabilities),
                    },
                )
            self._emit("connected" if result.success else "connect_failed", result)
            return result

    def disconnect(self) -> RobotResult:
        with self._lock:
            result = self._robot.disconnect()
            self._emit("disconnected", result)
            return result

    def execute(self, command: RobotCommand) -> RobotResult:
        with self._lock:
            self._counter += 1
            command_id = command.command_id or f"session-{self._counter:04d}"
            assigned_command = replace(command, command_id=command_id)
            if self._journal is not None:
                self._journal.record_command(command_id, assigned_command)
                self._journal.record_transition(
                    command_id,
                    CommandStatus.SUBMITTED,
                    StatusEvidence.APPLICATION_DERIVED,
                    "application submitted command",
                )
            result = self._robot.execute(assigned_command)
            if self._journal is not None:
                assert result.status is not None
                self._journal.record_transition(
                    result.command_id or command_id,
                    result.status,
                    result.status_evidence,
                    result.message,
                )
                self._journal.record_result(command.kind.value, result)
                if result.state.fault is not None:
                    self._journal.append("fault", {"fault": result.state.fault})
            self._emit("command_result", result)
            return result

    def stop(self) -> RobotResult:
        with self._lock:
            result = self._robot.stop()
            if self._journal is not None:
                self._journal.record_result("STOP", result)
            self._emit("stopped", result)
            return result

    def refresh(self) -> RobotState:
        with self._lock:
            state = self._robot.get_state()
            if self._journal is not None:
                self._journal.record_state(state, "refresh")
            return state
