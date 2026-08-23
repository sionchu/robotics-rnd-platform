"""Backend protocol and deterministic fake for the Rainbow adapter."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol


class RainbowBackendError(RuntimeError):
    pass


class RainbowConnectionError(RainbowBackendError):
    pass


class RainbowTimeoutError(RainbowBackendError):
    pass


class FaultScenario(StrEnum):
    CONNECT_TIMEOUT = "connect_timeout"
    CONNECTION_DROP_DURING_COMMAND = "connection_drop_during_command"
    COMMAND_REJECTED = "command_rejected"
    MOTION_TIMEOUT = "motion_timeout"
    CONTROLLER_FAULT = "controller_fault"
    DIGITAL_IO_FAILURE = "digital_io_failure"
    STALE_STATE = "stale_state"
    DELAYED_RESPONSE = "delayed_response"
    DUPLICATE_RESPONSE = "duplicate_response"
    UNEXPECTED_RESPONSE = "unexpected_response"


@dataclass(frozen=True, slots=True)
class VendorState:
    connected: bool
    joint_angles_deg: tuple[float, ...]
    tcp_pose_mm_deg: tuple[float, float, float, float, float, float]
    robot_state: str = "IDLE"
    task_state: int | str | None = None
    speed_ratio: float | None = 1.0
    digital_inputs: tuple[bool, ...] = ()
    digital_outputs: tuple[bool, ...] = ()
    source_timestamp: datetime | None = None
    fault_code: str | None = None
    fault_message: str | None = None


@dataclass(frozen=True, slots=True)
class VendorCommandOutcome:
    accepted: bool
    completed: bool
    message: str
    code: str | None = None
    timed_out: bool = False
    diagnostics: tuple[str, ...] = ()


class RainbowBackend(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def connect(self, timeout_s: float) -> None: ...

    def disconnect(self) -> None: ...

    def read_state(self, timeout_s: float) -> VendorState: ...

    def move_joint(
        self,
        positions_deg: tuple[float, ...],
        speed_deg_s: float,
        acceleration_deg_s2: float,
        timeout_s: float,
    ) -> VendorCommandOutcome: ...

    def move_linear(
        self,
        pose_mm_deg: tuple[float, float, float, float, float, float],
        speed_mm_s: float,
        acceleration_mm_s2: float,
        timeout_s: float,
    ) -> VendorCommandOutcome: ...

    def stop(self, timeout_s: float) -> VendorCommandOutcome: ...

    def pause(self, timeout_s: float) -> VendorCommandOutcome: ...

    def resume(self, timeout_s: float) -> VendorCommandOutcome: ...

    def reset_fault(self, timeout_s: float) -> VendorCommandOutcome: ...

    def write_digital_output(self, channel: int, value: bool, timeout_s: float) -> VendorCommandOutcome: ...


class FakeRainbowBackend:
    """Contract fake only; state changes are scripted and are not robot physics."""

    def __init__(self, faults: Iterable[FaultScenario | str] = ()) -> None:
        self._faults = deque(FaultScenario(fault) for fault in faults)
        self._connected = False
        self._joint_angles_deg: tuple[float, ...] = (0.0,) * 6
        self._tcp_pose_mm_deg = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self._robot_state = "IDLE"
        self._digital_inputs: tuple[bool, ...] = (False,) * 16
        self._digital_outputs: tuple[bool, ...] = (False,) * 16
        self._fault_code: str | None = None
        self._fault_message: str | None = None
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return "fake-rainbow"

    @property
    def version(self) -> str:
        return "contract-v1"

    def inject(self, scenario: FaultScenario | str) -> None:
        self._faults.append(FaultScenario(scenario))

    def _take(self, scenario: FaultScenario) -> bool:
        if self._faults and self._faults[0] is scenario:
            self._faults.popleft()
            return True
        return False

    def _require_connected(self) -> None:
        if not self._connected:
            raise RainbowConnectionError("fake Rainbow backend is disconnected")

    def connect(self, timeout_s: float) -> None:
        self.calls.append(f"connect:{timeout_s}")
        if self._take(FaultScenario.CONNECT_TIMEOUT):
            raise RainbowTimeoutError("injected connection timeout")
        self._connected = True

    def disconnect(self) -> None:
        self.calls.append("disconnect")
        self._connected = False

    def read_state(self, timeout_s: float) -> VendorState:
        self._require_connected()
        self.calls.append(f"read_state:{timeout_s}")
        source_timestamp = datetime.now(UTC)
        if self._take(FaultScenario.STALE_STATE):
            source_timestamp -= timedelta(seconds=60)
        if self._take(FaultScenario.CONTROLLER_FAULT):
            self._robot_state = "FAULT"
            self._fault_code = "INJECTED_CONTROLLER_FAULT"
            self._fault_message = "injected controller fault"
        return VendorState(
            connected=True,
            joint_angles_deg=self._joint_angles_deg,
            tcp_pose_mm_deg=self._tcp_pose_mm_deg,
            robot_state=self._robot_state,
            digital_inputs=self._digital_inputs,
            digital_outputs=self._digital_outputs,
            source_timestamp=source_timestamp,
            fault_code=self._fault_code,
            fault_message=self._fault_message,
        )

    def _outcome(self, operation: str) -> VendorCommandOutcome:
        self._require_connected()
        self.calls.append(operation)
        if self._take(FaultScenario.CONNECTION_DROP_DURING_COMMAND):
            self._connected = False
            raise RainbowConnectionError("injected connection drop during command")
        if self._take(FaultScenario.COMMAND_REJECTED):
            return VendorCommandOutcome(False, False, "injected command rejection", "COMMAND_REJECTED")
        if self._take(FaultScenario.MOTION_TIMEOUT):
            return VendorCommandOutcome(True, False, "injected motion timeout", "MOTION_TIMEOUT", True)
        if self._take(FaultScenario.CONTROLLER_FAULT):
            self._robot_state = "FAULT"
            self._fault_code = "INJECTED_CONTROLLER_FAULT"
            self._fault_message = "injected controller fault"
            return VendorCommandOutcome(False, False, self._fault_message, self._fault_code)
        diagnostics: list[str] = []
        if self._take(FaultScenario.DELAYED_RESPONSE):
            diagnostics.append("injected_delayed_response")
        if self._take(FaultScenario.DUPLICATE_RESPONSE):
            diagnostics.append("injected_duplicate_response_ignored")
        if self._take(FaultScenario.UNEXPECTED_RESPONSE):
            diagnostics.append("injected_unexpected_response_quarantined")
        return VendorCommandOutcome(True, True, "fake command completed", diagnostics=tuple(diagnostics))

    def move_joint(
        self,
        positions_deg: tuple[float, ...],
        speed_deg_s: float,
        acceleration_deg_s2: float,
        timeout_s: float,
    ) -> VendorCommandOutcome:
        outcome = self._outcome(f"move_joint:{speed_deg_s}:{acceleration_deg_s2}:{timeout_s}")
        if outcome.completed:
            self._joint_angles_deg = tuple(positions_deg)
        return outcome

    def move_linear(
        self,
        pose_mm_deg: tuple[float, float, float, float, float, float],
        speed_mm_s: float,
        acceleration_mm_s2: float,
        timeout_s: float,
    ) -> VendorCommandOutcome:
        outcome = self._outcome(f"move_linear:{speed_mm_s}:{acceleration_mm_s2}:{timeout_s}")
        if outcome.completed:
            self._tcp_pose_mm_deg = pose_mm_deg
        return outcome

    def stop(self, timeout_s: float) -> VendorCommandOutcome:
        outcome = self._outcome(f"stop:{timeout_s}")
        if outcome.completed:
            self._robot_state = "STOPPED"
        return outcome

    def pause(self, timeout_s: float) -> VendorCommandOutcome:
        outcome = self._outcome(f"pause:{timeout_s}")
        if outcome.completed:
            self._robot_state = "PAUSED"
        return outcome

    def resume(self, timeout_s: float) -> VendorCommandOutcome:
        outcome = self._outcome(f"resume:{timeout_s}")
        if outcome.completed:
            self._robot_state = "IDLE"
        return outcome

    def reset_fault(self, timeout_s: float) -> VendorCommandOutcome:
        outcome = self._outcome(f"reset_fault:{timeout_s}")
        if outcome.completed:
            self._robot_state = "IDLE"
            self._fault_code = None
            self._fault_message = None
        return outcome

    def write_digital_output(self, channel: int, value: bool, timeout_s: float) -> VendorCommandOutcome:
        self._require_connected()
        self.calls.append(f"write_digital_output:{channel}:{value}:{timeout_s}")
        if self._take(FaultScenario.DIGITAL_IO_FAILURE):
            return VendorCommandOutcome(False, False, "injected digital I/O failure", "DIGITAL_IO_FAILURE")
        if channel < 0 or channel >= len(self._digital_outputs):
            return VendorCommandOutcome(False, False, "digital output channel unavailable", "INVALID_CHANNEL")
        values = list(self._digital_outputs)
        values[channel] = value
        self._digital_outputs = tuple(values)
        return VendorCommandOutcome(True, True, "fake digital output updated")
