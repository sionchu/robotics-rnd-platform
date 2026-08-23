from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import Lock, Thread
from time import sleep

import pytest

from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Pose, Quaternion, Vector3
from robotics_rnd.drivers.rainbow import (
    FakeRainbowBackend,
    FaultScenario,
    RainbowConfig,
    RainbowOperationMode,
    RainbowRobotDriver,
    RbpodoBackend,
    VendorState,
)
from robotics_rnd.robot import CommandStatus, ConnectionState, RobotCapability, RobotCommand
from robotics_rnd.robot.errors import UnsupportedRobotCapability


def _fake_driver(
    *faults: FaultScenario, motion: bool = True, io_write: bool = True
) -> tuple[RainbowRobotDriver, FakeRainbowBackend]:
    backend = FakeRainbowBackend(faults)
    driver = RainbowRobotDriver(
        RainbowConfig(
            operation_mode=RainbowOperationMode.FAKE,
            motion_enabled=motion,
            io_write_enabled=io_write,
        ),
        backend,
    )
    return driver, backend


def test_default_configuration_is_read_only_and_never_claims_motion() -> None:
    driver = RainbowRobotDriver(RainbowConfig(), FakeRainbowBackend())
    assert driver.capabilities == frozenset(
        {RobotCapability.GET_STATE, RobotCapability.DIGITAL_INPUT, RobotCapability.REALTIME_STATE}
    )
    assert driver.connect().success
    with pytest.raises(UnsupportedRobotCapability):
        driver.execute(RobotCommand.move_joint((0.0,) * 6))


def test_fake_joint_linear_and_digital_mapping() -> None:
    driver, _ = _fake_driver()
    assert driver.connect().success
    joint = driver.execute(RobotCommand.move_joint((0.0, 0.1, -0.2, 0.3, -0.4, 0.5)))
    assert joint.status is CommandStatus.COMPLETED
    assert joint.state.joints.positions_rad == pytest.approx((0.0, 0.1, -0.2, 0.3, -0.4, 0.5))
    target = Pose(Vector3(0.1, -0.2, 0.3), Quaternion.identity(), FrameId("robot_base"))
    linear = driver.execute(RobotCommand.move_linear(target))
    assert linear.state.tool_pose.position_m.as_array() == pytest.approx((0.1, -0.2, 0.3))
    output = driver.write_digital_output(2, True)
    assert output.state.digital_outputs[2]


@pytest.mark.parametrize(
    ("scenario", "expected_status", "error_code"),
    [
        (FaultScenario.COMMAND_REJECTED, CommandStatus.FAILED, "COMMAND_REJECTED"),
        (FaultScenario.MOTION_TIMEOUT, CommandStatus.TIMED_OUT, "MOTION_TIMEOUT"),
    ],
)
def test_command_failure_mapping(
    scenario: FaultScenario, expected_status: CommandStatus, error_code: str
) -> None:
    driver, _ = _fake_driver(scenario)
    driver.connect()
    result = driver.execute(RobotCommand.move_joint((0.0,) * 6))
    assert result.status is expected_status
    assert result.error_code == error_code


def test_controller_fault_during_command_is_failed_and_preserved_in_state() -> None:
    driver, backend = _fake_driver()
    driver.connect()
    backend.inject(FaultScenario.CONTROLLER_FAULT)
    result = driver.execute(RobotCommand.move_joint((0.0,) * 6))
    assert result.status is CommandStatus.FAILED
    assert result.error_code == "INJECTED_CONTROLLER_FAULT"
    assert result.state.fault_message == "injected controller fault"


def test_connection_drop_marks_outcome_unknown_and_requires_resync_acknowledgement() -> None:
    driver, backend = _fake_driver(FaultScenario.CONNECTION_DROP_DURING_COMMAND)
    driver.connect()
    uncertain = driver.execute(RobotCommand.move_joint((0.1,) * 6))
    assert uncertain.status is CommandStatus.UNKNOWN
    assert driver.motion_locked
    assert driver.uncertain_command_id == uncertain.command_id
    assert driver.reconnect().success
    blocked = driver.execute(RobotCommand.move_joint((0.0,) * 6))
    assert blocked.error_code == "RESYNC_REQUIRED"
    assert not any("resume" in call for call in backend.calls)
    driver.acknowledge_resync()
    assert not driver.motion_locked
    assert driver.execute(RobotCommand.move_joint((0.0,) * 6)).success


def test_connect_timeout_is_a_failed_result_not_a_false_connection() -> None:
    driver, _ = _fake_driver(FaultScenario.CONNECT_TIMEOUT)
    result = driver.connect()
    assert not result.success
    assert result.error_code == "CONNECT_FAILED"
    assert not result.state.connected
    assert result.state.connection_state is ConnectionState.FAULTED


def test_stale_state_is_exposed_as_degraded_evidence() -> None:
    driver, backend = _fake_driver()
    driver.connect()
    backend.inject(FaultScenario.STALE_STATE)
    state = driver.get_state()
    assert state.connection_state is ConnectionState.DEGRADED
    assert state.fault is not None
    assert state.fault.code == "STALE_STATE"


def test_response_anomalies_are_quarantined_as_diagnostics() -> None:
    driver, _ = _fake_driver(
        FaultScenario.DELAYED_RESPONSE,
        FaultScenario.DUPLICATE_RESPONSE,
        FaultScenario.UNEXPECTED_RESPONSE,
    )
    driver.connect()
    result = driver.execute(RobotCommand.move_joint((0.0,) * 6))
    events = result.diagnostics["backend_events"]
    assert events == [
        "injected_delayed_response",
        "injected_duplicate_response_ignored",
        "injected_unexpected_response_quarantined",
    ]


def test_vendor_state_timestamp_is_distinct_from_host_receipt_time() -> None:
    source_time = datetime.now(UTC) - timedelta(milliseconds=10)
    vendor = VendorState(
        True,
        (0.0,) * 6,
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        source_timestamp=source_time,
    )
    assert vendor.source_timestamp is source_time


def test_live_configuration_requires_host_and_disallows_auto_reconnect() -> None:
    with pytest.raises(ValueError, match="host"):
        RainbowConfig(operation_mode=RainbowOperationMode.LIVE_MANUAL)
    with pytest.raises(ValueError, match="automatic reconnect"):
        RainbowConfig(auto_reconnect=True)


def test_disconnect_has_explicit_shutdown_state_and_backend_call() -> None:
    driver, backend = _fake_driver()
    driver.connect()
    result = driver.disconnect()
    assert result.success
    assert not result.state.connected
    assert result.state.connection_state is ConnectionState.DISCONNECTED
    assert backend.calls[-1] == "disconnect"


def test_adapter_tracks_bounded_liveness_summary() -> None:
    driver, _ = _fake_driver()
    assert driver.connection_age_s is None
    driver.connect()
    assert driver.connection_age_s is not None
    assert driver.last_successful_state_at is not None
    assert driver.last_response_at is not None
    assert driver.consecutive_failures == 0
    driver.disconnect()
    assert driver.connection_age_s is None


def test_shutdown_after_failed_reconnect_is_deterministic() -> None:
    driver, backend = _fake_driver(FaultScenario.CONNECTION_DROP_DURING_COMMAND)
    driver.connect()
    driver.execute(RobotCommand.move_joint((0.1,) * 6))
    backend.inject(FaultScenario.CONNECT_TIMEOUT)
    reconnect = driver.reconnect()
    assert not reconnect.success
    assert reconnect.state.connection_state is ConnectionState.FAULTED
    shutdown = driver.disconnect()
    assert shutdown.state.connection_state is ConnectionState.DISCONNECTED
    assert driver.motion_locked


def test_adapter_serializes_backend_calls() -> None:
    class TrackingBackend(FakeRainbowBackend):
        def __init__(self) -> None:
            super().__init__()
            self.guard = Lock()
            self.active = 0
            self.max_active = 0

        def read_state(self, timeout_s: float) -> VendorState:
            with self.guard:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            sleep(0.005)
            try:
                return super().read_state(timeout_s)
            finally:
                with self.guard:
                    self.active -= 1

    backend = TrackingBackend()
    driver = RainbowRobotDriver(RainbowConfig(operation_mode=RainbowOperationMode.FAKE), backend)
    driver.connect()
    threads = [Thread(target=driver.get_state) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert backend.max_active == 1


def test_vendor_array_shape_is_validated() -> None:
    class BadShapeBackend(FakeRainbowBackend):
        def read_state(self, timeout_s: float) -> VendorState:
            state = super().read_state(timeout_s)
            return VendorState(
                state.connected,
                (0.0,),
                state.tcp_pose_mm_deg,
                source_timestamp=state.source_timestamp,
            )

    driver = RainbowRobotDriver(RainbowConfig(operation_mode=RainbowOperationMode.FAKE), BadShapeBackend())
    result = driver.connect()
    assert not result.success
    assert result.error_code == "CONNECT_FAILED"


def test_rbpodo_backend_construction_is_lazy_and_version_guarded(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = RbpodoBackend("controller.example.invalid")
    monkeypatch.setattr("robotics_rnd.drivers.rainbow.rbpodo_backend.metadata.version", lambda _: "0.15.0")
    with pytest.raises(RuntimeError, match="unsupported rbpodo version"):
        backend.connect(0.1)
