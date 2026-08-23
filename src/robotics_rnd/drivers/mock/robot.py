"""Deterministic contract mock; it does not simulate robot physics."""

from __future__ import annotations

from datetime import UTC, datetime

from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Pose
from robotics_rnd.robot import (
    CommandKind,
    JointState,
    RobotCapability,
    RobotCommand,
    RobotInterface,
    RobotMode,
    RobotResult,
    RobotState,
)
from robotics_rnd.robot.errors import RobotFault, RobotNotConnected


class MockRobot(RobotInterface):
    def __init__(self, joint_names: tuple[str, ...] | None = None, base_frame: FrameId | None = None) -> None:
        self._joint_names = joint_names or tuple(f"joint_{index}" for index in range(1, 7))
        self._base_frame = base_frame or FrameId("robot_base")
        self._connected = False
        self._mode = RobotMode.DISCONNECTED
        self._joints = JointState(self._joint_names, tuple(0.0 for _ in self._joint_names))
        self._tool_pose = Pose.identity(self._base_frame)
        self._fault_message: str | None = None
        self._command_counter = 0

    @property
    def capabilities(self) -> frozenset[RobotCapability]:
        return frozenset(
            {
                RobotCapability.GET_STATE,
                RobotCapability.MOVE_JOINT,
                RobotCapability.MOVE_LINEAR,
                RobotCapability.STOP,
                RobotCapability.RESET_FAULT,
            }
        )

    def _state(self) -> RobotState:
        return RobotState(
            connected=self._connected,
            mode=self._mode,
            joints=self._joints,
            tool_pose=self._tool_pose,
            timestamp=datetime.now(UTC),
            fault_message=self._fault_message,
        )

    def connect(self) -> RobotResult:
        self._connected = True
        self._mode = RobotMode.IDLE
        self._fault_message = None
        return RobotResult(True, "mock robot connected", self._state())

    def disconnect(self) -> RobotResult:
        self._connected = False
        self._mode = RobotMode.DISCONNECTED
        self._fault_message = None
        return RobotResult(True, "mock robot disconnected", self._state())

    def get_state(self) -> RobotState:
        return self._state()

    def _require_ready_for_command(self) -> None:
        if not self._connected:
            raise RobotNotConnected("robot command requires an active connection")
        if self._mode is RobotMode.FAULT:
            raise RobotFault(self._fault_message or "robot is faulted")

    def execute(self, command: RobotCommand) -> RobotResult:
        self._require_ready_for_command()
        if command.kind is CommandKind.STOP:
            return self.stop()
        if command.kind is CommandKind.MOVE_JOINT:
            self.require_capability(RobotCapability.MOVE_JOINT)
            assert command.joint_positions_rad is not None
            if len(command.joint_positions_rad) != len(self._joint_names):
                raise ValueError("joint command count does not match mock robot joints")
            self._mode = RobotMode.MOVING
            self._joints = JointState(self._joint_names, command.joint_positions_rad)
        elif command.kind is CommandKind.MOVE_LINEAR:
            self.require_capability(RobotCapability.MOVE_LINEAR)
            assert command.target_pose is not None
            if command.target_pose.frame != self._base_frame:
                raise ValueError(f"linear target must be in {self._base_frame}")
            self._mode = RobotMode.MOVING
            self._tool_pose = command.target_pose
        self._mode = RobotMode.IDLE
        self._command_counter += 1
        command_id = f"mock-{self._command_counter:04d}"
        return RobotResult(True, "mock command completed", self._state(), command_id)

    def stop(self) -> RobotResult:
        if not self._connected:
            raise RobotNotConnected("stop requires an active connection")
        self._mode = RobotMode.STOPPED
        return RobotResult(True, "mock robot stopped", self._state())

    def inject_fault(self, message: str = "injected test fault") -> RobotState:
        if not self._connected:
            raise RobotNotConnected("fault injection requires an active connection")
        self._fault_message = message
        self._mode = RobotMode.FAULT
        return self._state()

    def reset_fault(self) -> RobotResult:
        if not self._connected:
            raise RobotNotConnected("fault reset requires an active connection")
        self._fault_message = None
        self._mode = RobotMode.IDLE
        return RobotResult(True, "mock fault reset", self._state())
