"""Rainbow Robotics adapter with conservative lifecycle and reconnect semantics."""

from __future__ import annotations

from datetime import UTC, datetime
from math import degrees
from threading import RLock

from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Pose
from robotics_rnd.robot import (
    CommandKind,
    CommandStatus,
    ConnectionState,
    FaultCategory,
    FaultSeverity,
    JointState,
    RobotCapability,
    RobotCommand,
    RobotFaultRecord,
    RobotInterface,
    RobotMode,
    RobotResult,
    RobotState,
    StatusEvidence,
)
from robotics_rnd.robot.errors import DriverUnavailable, RobotNotConnected

from .backend import (
    RainbowBackend,
    RainbowBackendError,
    RainbowConnectionError,
    RainbowTimeoutError,
    VendorCommandOutcome,
    VendorState,
)
from .config import RainbowConfig, RainbowOperationMode
from .mapping import degrees_to_radians, platform_pose_to_vendor, radians_to_degrees, vendor_pose_to_platform


class RainbowRobotDriver(RobotInterface):
    """Adapter boundary; default construction remains inert and opens no connection."""

    _MESSAGE = (
        "Rainbow adapter is not configured. Inject an approved rbpodo-compatible backend and explicit "
        "RainbowConfig; live use also requires controller/network/safety validation."
    )

    def __init__(self, config: RainbowConfig | None = None, backend: RainbowBackend | None = None) -> None:
        if (config is None) != (backend is None):
            raise ValueError("Rainbow config and backend must be provided together")
        self._config = config
        self._backend = backend
        self._lock = RLock()
        self._counter = 0
        self._connected = False
        self._connection_state = ConnectionState.DISCONNECTED
        self._last_vendor_state: VendorState | None = None
        self._last_fault: RobotFaultRecord | None = None
        self._motion_locked = False
        self._uncertain_command_id: str | None = None
        self._connected_at: datetime | None = None
        self._last_successful_state_at: datetime | None = None
        self._last_response_at: datetime | None = None
        self._consecutive_failures = 0

    @property
    def capabilities(self) -> frozenset[RobotCapability]:
        if self._config is None:
            return frozenset()
        capabilities = {
            RobotCapability.GET_STATE,
            RobotCapability.DIGITAL_INPUT,
            RobotCapability.REALTIME_STATE,
        }
        if self._config.io_write_enabled:
            capabilities.add(RobotCapability.DIGITAL_OUTPUT)
        if self._config.motion_enabled:
            capabilities.update(
                {
                    RobotCapability.MOVE_JOINT,
                    RobotCapability.MOVE_LINEAR,
                    RobotCapability.STOP,
                    RobotCapability.CONTROLLED_STOP,
                    RobotCapability.PAUSE_RESUME,
                }
            )
        if self._config.operation_mode is RainbowOperationMode.FAKE:
            capabilities.add(RobotCapability.RESET_FAULT)
        return frozenset(capabilities)

    @property
    def motion_locked(self) -> bool:
        return self._motion_locked

    @property
    def uncertain_command_id(self) -> str | None:
        return self._uncertain_command_id

    @property
    def last_successful_state_at(self) -> datetime | None:
        return self._last_successful_state_at

    @property
    def last_response_at(self) -> datetime | None:
        return self._last_response_at

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    @property
    def connection_age_s(self) -> float | None:
        if self._connected_at is None or not self._connected:
            return None
        return (datetime.now(UTC) - self._connected_at).total_seconds()

    def _require_configured(self) -> tuple[RainbowConfig, RainbowBackend]:
        if self._config is None or self._backend is None:
            raise DriverUnavailable(self._MESSAGE)
        return self._config, self._backend

    def _empty_state(self) -> RobotState:
        config, _ = self._require_configured()
        names = tuple(f"joint_{index}" for index in range(1, config.expected_joint_count + 1))
        return RobotState(
            connected=False,
            mode=RobotMode.DISCONNECTED,
            joints=JointState(names, (0.0,) * config.expected_joint_count),
            tool_pose=Pose.identity(FrameId(config.base_frame)),
            connection_state=self._connection_state,
            fault_message=self._last_fault.message if self._last_fault else None,
            fault=self._last_fault,
        )

    @staticmethod
    def _map_mode(vendor: VendorState) -> RobotMode:
        normalized = vendor.robot_state.upper()
        if vendor.fault_message or normalized == "FAULT":
            return RobotMode.FAULT
        return {
            "IDLE": RobotMode.IDLE,
            "MOVING": RobotMode.MOVING,
            "PAUSED": RobotMode.PAUSED,
            "STOPPED": RobotMode.STOPPED,
        }.get(normalized, RobotMode.UNKNOWN)

    def _map_state(self, vendor: VendorState) -> RobotState:
        config, _ = self._require_configured()
        if len(vendor.joint_angles_deg) != config.expected_joint_count:
            raise ValueError(
                f"Rainbow state contains {len(vendor.joint_angles_deg)} joints; "
                f"expected {config.expected_joint_count}"
            )
        fault = self._last_fault
        if vendor.fault_message:
            fault = RobotFaultRecord(
                FaultCategory.CONTROLLER,
                FaultSeverity.ERROR,
                vendor.fault_code or "CONTROLLER_FAULT",
                vendor.fault_message,
                recoverable=False,
                source="rainbow-backend",
                raw_vendor_context={"vendor_code": vendor.fault_code},
            )
            self._last_fault = fault
        now = datetime.now(UTC)
        if (
            vendor.source_timestamp is not None
            and (now - vendor.source_timestamp).total_seconds() > config.stale_state_after_s
        ):
            fault = RobotFaultRecord(
                FaultCategory.STALE_STATE,
                FaultSeverity.WARNING,
                "STALE_STATE",
                "Rainbow state exceeded the configured freshness limit",
                recoverable=True,
                source="rainbow-adapter",
            )
            self._last_fault = fault
            self._connection_state = ConnectionState.DEGRADED
        return RobotState(
            connected=True,
            mode=self._map_mode(vendor),
            joints=JointState(
                tuple(f"joint_{index}" for index in range(1, config.expected_joint_count + 1)),
                degrees_to_radians(vendor.joint_angles_deg),
            ),
            tool_pose=vendor_pose_to_platform(vendor.tcp_pose_mm_deg, FrameId(config.base_frame)),
            timestamp=now,
            source_timestamp=vendor.source_timestamp,
            connection_state=self._connection_state,
            fault_message=fault.message if fault else None,
            fault=fault,
            task_state=vendor.task_state,
            speed_ratio=vendor.speed_ratio,
            digital_inputs=vendor.digital_inputs,
            digital_outputs=vendor.digital_outputs,
        )

    def connect(self) -> RobotResult:
        config, backend = self._require_configured()
        with self._lock:
            self._connection_state = ConnectionState.CONNECTING
            try:
                backend.connect(config.connect_timeout_s)
                self._connected = True
                self._connection_state = ConnectionState.CONNECTED
                self._connected_at = datetime.now(UTC)
                self._last_vendor_state = backend.read_state(config.state_timeout_s)
                state = self._map_state(self._last_vendor_state)
                self._last_successful_state_at = state.timestamp
                self._last_response_at = state.timestamp
                self._consecutive_failures = 0
                return RobotResult(True, "Rainbow backend connected and state synchronized", state)
            except (RainbowBackendError, ImportError, OSError, RuntimeError, ValueError) as error:
                self._connected = False
                self._connected_at = None
                self._connection_state = ConnectionState.FAULTED
                self._last_fault = RobotFaultRecord(
                    FaultCategory.COMMUNICATION,
                    FaultSeverity.ERROR,
                    "CONNECT_FAILED",
                    str(error),
                    recoverable=True,
                    source=backend.name,
                )
                self._consecutive_failures += 1
                return RobotResult(
                    False,
                    f"Rainbow connection failed: {error}",
                    self._empty_state(),
                    status=CommandStatus.FAILED,
                    error_code="CONNECT_FAILED",
                )

    def disconnect(self) -> RobotResult:
        _, backend = self._require_configured()
        with self._lock:
            self._connection_state = ConnectionState.SHUTTING_DOWN
            backend.disconnect()
            self._connected = False
            self._connected_at = None
            self._connection_state = ConnectionState.DISCONNECTED
            self._last_vendor_state = None
            return RobotResult(True, "Rainbow backend disconnected", self._empty_state())

    def get_state(self) -> RobotState:
        config, backend = self._require_configured()
        with self._lock:
            if not self._connected:
                return self._empty_state()
            try:
                vendor = backend.read_state(config.state_timeout_s)
                self._last_vendor_state = vendor
                state = self._map_state(vendor)
                self._last_successful_state_at = state.timestamp
                self._last_response_at = state.timestamp
                self._consecutive_failures = 0
                return state
            except (RainbowConnectionError, RainbowTimeoutError, OSError) as error:
                self._mark_uncertain(None, error)
                return self._empty_state()

    def _next_id(self, command: RobotCommand) -> str:
        if command.command_id:
            return command.command_id
        self._counter += 1
        return f"rainbow-{self._counter:04d}"

    def _mark_uncertain(self, command_id: str | None, error: BaseException) -> None:
        self._connected = False
        self._connected_at = None
        self._connection_state = ConnectionState.DEGRADED
        self._motion_locked = True
        self._uncertain_command_id = command_id
        self._last_fault = RobotFaultRecord(
            FaultCategory.COMMUNICATION,
            FaultSeverity.ERROR,
            "CONNECTION_LOST",
            str(error),
            recoverable=True,
            source="rainbow-backend",
        )
        self._consecutive_failures += 1

    def _result_from_outcome(
        self, command_id: str, outcome: VendorCommandOutcome, started_at: datetime
    ) -> RobotResult:
        if outcome.completed:
            status = CommandStatus.COMPLETED
        elif outcome.timed_out:
            status = CommandStatus.TIMED_OUT
        elif outcome.accepted:
            status = CommandStatus.ACCEPTED
        else:
            status = CommandStatus.FAILED
        success = outcome.accepted and not outcome.timed_out
        self._last_response_at = datetime.now(UTC)
        self._consecutive_failures = 0
        if not success:
            category = FaultCategory.MOTION
            if outcome.code == "DIGITAL_IO_FAILURE":
                category = FaultCategory.IO
            elif outcome.code == "INJECTED_CONTROLLER_FAULT":
                category = FaultCategory.CONTROLLER
            self._last_fault = RobotFaultRecord(
                category,
                FaultSeverity.ERROR,
                outcome.code or "COMMAND_FAILED",
                outcome.message,
                recoverable=outcome.timed_out or outcome.code == "COMMAND_REJECTED",
                source="rainbow-backend",
                raw_vendor_context={"vendor_code": outcome.code},
            )
        return RobotResult(
            success,
            outcome.message,
            self.get_state(),
            command_id,
            status=status,
            status_evidence=StatusEvidence.VENDOR_REPORTED,
            started_at=started_at,
            completed_at=datetime.now(UTC) if outcome.completed else None,
            error_code=outcome.code,
            diagnostics={"backend_events": list(outcome.diagnostics)},
            vendor_code=outcome.code,
        )

    def execute(self, command: RobotCommand) -> RobotResult:
        config, backend = self._require_configured()
        with self._lock:
            if not self._connected:
                raise RobotNotConnected("Rainbow command requires an active connection")
            command_id = self._next_id(command)
            started_at = datetime.now(UTC)
            is_motion = command.kind in {CommandKind.MOVE_JOINT, CommandKind.MOVE_LINEAR}
            if is_motion and self._motion_locked:
                return RobotResult(
                    False,
                    "motion is locked until post-reconnect state is reviewed and acknowledged",
                    self.get_state(),
                    command_id,
                    status=CommandStatus.FAILED,
                    error_code="RESYNC_REQUIRED",
                )
            timeout = command.timeout_s or config.command_timeout_s
            try:
                if command.kind is CommandKind.MOVE_JOINT:
                    self.require_capability(RobotCapability.MOVE_JOINT)
                    assert command.joint_positions_rad is not None
                    if len(command.joint_positions_rad) != config.expected_joint_count:
                        raise ValueError("Rainbow joint command count does not match configured joints")
                    outcome = backend.move_joint(
                        radians_to_degrees(command.joint_positions_rad),
                        degrees(command.joint_speed_rad_s or 0.25),
                        degrees(command.joint_acceleration_rad_s2 or 0.5),
                        timeout,
                    )
                elif command.kind is CommandKind.MOVE_LINEAR:
                    self.require_capability(RobotCapability.MOVE_LINEAR)
                    assert command.target_pose is not None
                    outcome = backend.move_linear(
                        platform_pose_to_vendor(command.target_pose, FrameId(config.base_frame)),
                        (command.linear_speed_m_s or 0.05) * 1000.0,
                        (command.linear_acceleration_m_s2 or 0.1) * 1000.0,
                        timeout,
                    )
                elif command.kind is CommandKind.STOP:
                    self.require_capability(RobotCapability.STOP)
                    outcome = backend.stop(timeout)
                elif command.kind is CommandKind.PAUSE:
                    self.require_capability(RobotCapability.PAUSE_RESUME)
                    outcome = backend.pause(timeout)
                elif command.kind is CommandKind.RESUME:
                    self.require_capability(RobotCapability.PAUSE_RESUME)
                    outcome = backend.resume(timeout)
                elif command.kind is CommandKind.WRITE_DIGITAL_OUTPUT:
                    self.require_capability(RobotCapability.DIGITAL_OUTPUT)
                    assert command.digital_channel is not None
                    assert command.digital_value is not None
                    outcome = backend.write_digital_output(
                        command.digital_channel, command.digital_value, timeout
                    )
                else:
                    raise ValueError(f"unsupported Rainbow command: {command.kind.value}")
                return self._result_from_outcome(command_id, outcome, started_at)
            except (RainbowConnectionError, RainbowTimeoutError, OSError) as error:
                self._mark_uncertain(command_id, error)
                return RobotResult(
                    False,
                    f"Rainbow command outcome is unknown after connection loss: {error}",
                    self._empty_state(),
                    command_id,
                    status=CommandStatus.UNKNOWN,
                    status_evidence=StatusEvidence.ADAPTER_DERIVED,
                    started_at=started_at,
                    error_code="CONNECTION_LOST",
                )

    def stop(self) -> RobotResult:
        return self.execute(RobotCommand.stop())

    def reset_fault(self) -> RobotResult:
        config, backend = self._require_configured()
        self.require_capability(RobotCapability.RESET_FAULT)
        with self._lock:
            if not self._connected:
                raise RobotNotConnected("fault reset requires an active connection")
            outcome = backend.reset_fault(config.command_timeout_s)
            result = self._result_from_outcome("rainbow-reset-fault", outcome, datetime.now(UTC))
            if result.success:
                self._last_fault = None
            return result

    def reconnect(self) -> RobotResult:
        self._require_configured()
        with self._lock:
            self._connection_state = ConnectionState.RECONNECTING
            if self._connected:
                self.disconnect()
            result = self.connect()
            if result.success and self._uncertain_command_id is not None:
                self._motion_locked = True
            return result

    def acknowledge_resync(self) -> None:
        with self._lock:
            state = self.get_state()
            if not state.connected or state.mode in {RobotMode.MOVING, RobotMode.FAULT, RobotMode.UNKNOWN}:
                raise RuntimeError("cannot acknowledge Rainbow resync until state is connected and stable")
            self._motion_locked = False
            self._uncertain_command_id = None
            if self._connection_state is ConnectionState.DEGRADED:
                self._connection_state = ConnectionState.CONNECTED
