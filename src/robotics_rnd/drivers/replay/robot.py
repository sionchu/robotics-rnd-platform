"""Deterministic replay of platform JSONL journals with no vendor dependencies."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from robotics_rnd.robot import (
    CommandKind,
    ConnectionState,
    RobotCapability,
    RobotCommand,
    RobotInterface,
    RobotMode,
    RobotResult,
    RobotState,
)
from robotics_rnd.robot.errors import RobotNotConnected
from robotics_rnd.robot.journal import read_journal, result_from_json, state_from_json

_CAPABILITY_BY_COMMAND = {
    CommandKind.MOVE_JOINT.value: RobotCapability.MOVE_JOINT,
    CommandKind.MOVE_LINEAR.value: RobotCapability.MOVE_LINEAR,
    CommandKind.STOP.value: RobotCapability.STOP,
    CommandKind.PAUSE.value: RobotCapability.PAUSE_RESUME,
    CommandKind.RESUME.value: RobotCapability.PAUSE_RESUME,
    CommandKind.WRITE_DIGITAL_OUTPUT.value: RobotCapability.DIGITAL_OUTPUT,
}


class ReplayRobot(RobotInterface):
    def __init__(self, journal_path: Path) -> None:
        self._steps: list[tuple[str, RobotResult]] = []
        observed_states: list[RobotState] = []
        for record in read_journal(journal_path):
            if record.event_type == "command_result":
                result_payload = cast(Mapping[str, Any], record.payload["result"])
                self._steps.append((str(record.payload["command_kind"]), result_from_json(result_payload)))
            elif record.event_type == "state":
                state_payload = cast(Mapping[str, Any], record.payload["state"])
                observed_states.append(state_from_json(state_payload))
        if not self._steps and not observed_states:
            raise ValueError("robot replay journal contains no command results or states")
        self._template_state = self._steps[0][1].state if self._steps else observed_states[0]
        self._state = replace(
            self._template_state,
            connected=False,
            mode=RobotMode.DISCONNECTED,
            connection_state=ConnectionState.DISCONNECTED,
            fault_message=None,
            fault=None,
        )
        self._cursor = 0
        self._connected = False

    @property
    def capabilities(self) -> frozenset[RobotCapability]:
        capabilities = {RobotCapability.GET_STATE}
        for command_kind, _ in self._steps:
            capability = _CAPABILITY_BY_COMMAND.get(command_kind)
            if capability is not None:
                capabilities.add(capability)
        if RobotCapability.STOP in capabilities:
            capabilities.add(RobotCapability.CONTROLLED_STOP)
        return frozenset(capabilities)

    @property
    def remaining(self) -> int:
        return len(self._steps) - self._cursor

    def connect(self) -> RobotResult:
        self._connected = True
        self._state = replace(
            self._template_state,
            connected=True,
            connection_state=ConnectionState.CONNECTED,
        )
        return RobotResult(True, "replay robot connected", self._state)

    def disconnect(self) -> RobotResult:
        self._connected = False
        self._state = replace(
            self._state,
            connected=False,
            mode=RobotMode.DISCONNECTED,
            connection_state=ConnectionState.DISCONNECTED,
            fault_message=None,
            fault=None,
        )
        return RobotResult(True, "replay robot disconnected", self._state)

    def get_state(self) -> RobotState:
        return self._state

    def execute(self, command: RobotCommand) -> RobotResult:
        if not self._connected:
            raise RobotNotConnected("replay command requires an active replay session")
        if self._cursor >= len(self._steps):
            raise StopIteration("replay command results exhausted")
        expected_kind, recorded = self._steps[self._cursor]
        if expected_kind != command.kind.value:
            raise ValueError(
                f"replay expected {expected_kind} at step {self._cursor}, got {command.kind.value}"
            )
        self._cursor += 1
        self._state = recorded.state
        return recorded

    def stop(self) -> RobotResult:
        if self._cursor < len(self._steps) and self._steps[self._cursor][0] == CommandKind.STOP.value:
            return self.execute(RobotCommand.stop())
        if not self._connected:
            raise RobotNotConnected("replay stop requires an active replay session")
        self._state = replace(self._state, mode=RobotMode.STOPPED)
        return RobotResult(True, "replay robot stopped", self._state)

    def reset_fault(self) -> RobotResult:
        if not self._connected:
            raise RobotNotConnected("replay fault reset requires an active replay session")
        self._state = replace(self._state, mode=RobotMode.IDLE, fault_message=None, fault=None)
        return RobotResult(True, "replay fault reset", self._state)
