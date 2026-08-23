"""Capability-oriented robot contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum

from .commands import RobotCommand
from .errors import UnsupportedRobotCapability
from .models import RobotState
from .results import RobotResult


class RobotCapability(StrEnum):
    GET_STATE = "GET_STATE"
    MOVE_JOINT = "MOVE_JOINT"
    MOVE_LINEAR = "MOVE_LINEAR"
    STOP = "STOP"
    RESET_FAULT = "RESET_FAULT"
    DIGITAL_INPUT = "DIGITAL_INPUT"
    DIGITAL_OUTPUT = "DIGITAL_OUTPUT"
    PAUSE_RESUME = "PAUSE_RESUME"
    CONTROLLED_STOP = "CONTROLLED_STOP"
    ANALOG_INPUT = "ANALOG_INPUT"
    ANALOG_OUTPUT = "ANALOG_OUTPUT"
    TOOL_IO = "TOOL_IO"
    PAYLOAD_CONFIG = "PAYLOAD_CONFIG"
    TCP_CONFIG = "TCP_CONFIG"
    USER_FRAMES = "USER_FRAMES"
    TASK_PROGRAMS = "TASK_PROGRAMS"
    REALTIME_STATE = "REALTIME_STATE"


class RobotInterface(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> frozenset[RobotCapability]:
        raise NotImplementedError

    def require_capability(self, capability: RobotCapability) -> None:
        if capability not in self.capabilities:
            raise UnsupportedRobotCapability(f"robot does not support {capability.value}")

    @property
    def is_connected(self) -> bool:
        return self.get_state().connected

    @abstractmethod
    def connect(self) -> RobotResult:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> RobotResult:
        raise NotImplementedError

    @abstractmethod
    def get_state(self) -> RobotState:
        raise NotImplementedError

    @abstractmethod
    def execute(self, command: RobotCommand) -> RobotResult:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> RobotResult:
        raise NotImplementedError

    @abstractmethod
    def reset_fault(self) -> RobotResult:
        raise NotImplementedError

    def read_digital_input(self, channel: int) -> bool:
        self.require_capability(RobotCapability.DIGITAL_INPUT)
        state = self.get_state()
        try:
            return state.digital_inputs[channel]
        except IndexError as error:
            raise ValueError(f"digital input channel {channel} is unavailable") from error

    def write_digital_output(self, channel: int, value: bool) -> RobotResult:
        self.require_capability(RobotCapability.DIGITAL_OUTPUT)
        return self.execute(RobotCommand.write_digital_output(channel, value))

    def pause(self) -> RobotResult:
        self.require_capability(RobotCapability.PAUSE_RESUME)
        return self.execute(RobotCommand.pause())

    def resume(self) -> RobotResult:
        self.require_capability(RobotCapability.PAUSE_RESUME)
        return self.execute(RobotCommand.resume())

    def reconnect(self) -> RobotResult:
        if self.is_connected:
            self.disconnect()
        return self.connect()

    def acknowledge_resync(self) -> None:
        """Acknowledge state review after an uncertain reconnect, when supported."""

        raise UnsupportedRobotCapability("robot does not support reconnect resynchronization")
