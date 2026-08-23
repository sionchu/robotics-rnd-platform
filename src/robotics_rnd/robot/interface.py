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


class RobotInterface(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> frozenset[RobotCapability]:
        raise NotImplementedError

    def require_capability(self, capability: RobotCapability) -> None:
        if capability not in self.capabilities:
            raise UnsupportedRobotCapability(f"robot does not support {capability.value}")

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
