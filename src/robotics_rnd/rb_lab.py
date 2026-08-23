"""Reusable hardware-free RB Control Lab compositions."""

from __future__ import annotations

from pathlib import Path

from robotics_rnd.drivers.rainbow import (
    FakeRainbowBackend,
    FaultScenario,
    RainbowConfig,
    RainbowOperationMode,
    RainbowRobotDriver,
)
from robotics_rnd.drivers.replay import ReplayRobot
from robotics_rnd.robot import (
    RobotApplicationEvent,
    RobotApplicationService,
    RobotCommand,
    RobotJournal,
)


def run_mock_demo(journal_path: Path) -> dict[str, object]:
    journal_path.unlink(missing_ok=True)
    robot = RainbowRobotDriver(
        RainbowConfig(
            operation_mode=RainbowOperationMode.FAKE,
            motion_enabled=True,
            io_write_enabled=True,
        ),
        FakeRainbowBackend(),
    )
    service = RobotApplicationService(robot, RobotJournal(journal_path, "rb-control-lab-mock"))
    connected = service.connect()
    joint_command = RobotCommand.move_joint((0.0, 0.1, -0.2, 0.3, -0.1, 0.0))
    joint_result = service.execute(joint_command)
    io_result = service.execute(RobotCommand.write_digital_output(3, True))
    stopped = service.stop()
    service.disconnect()
    assert joint_result.status is not None
    assert io_result.status is not None

    replay = ReplayRobot(journal_path)
    replay_service = RobotApplicationService(replay)
    replay_service.connect()
    replay_joint = replay_service.execute(joint_command)
    replay_io = replay_service.execute(RobotCommand.write_digital_output(3, True))
    replay_stop = replay_service.stop()
    replay_service.disconnect()
    return {
        "status": "SOFTWARE_VALIDATED",
        "hardware_validation": False,
        "max_hardware_validation_level": 0,
        "backend": "fake-rainbow",
        "connected": connected.success,
        "joint_command_status": joint_result.status.value,
        "digital_output_status": io_result.status.value,
        "stopped": stopped.success,
        "journal": str(journal_path),
        "replay_matches": (
            replay_joint.status == joint_result.status
            and replay_io.status == io_result.status
            and replay_stop.status == stopped.status
        ),
    }


def run_fault_demo() -> dict[str, object]:
    backend = FakeRainbowBackend((FaultScenario.CONNECTION_DROP_DURING_COMMAND,))
    robot = RainbowRobotDriver(
        RainbowConfig(operation_mode=RainbowOperationMode.FAKE, motion_enabled=True), backend
    )
    events: list[RobotApplicationEvent] = []
    service = RobotApplicationService(robot)
    service.subscribe(events.append)
    service.connect()
    uncertain = service.execute(RobotCommand.move_joint((0.1,) * 6))
    reconnect = robot.reconnect()
    blocked = robot.execute(RobotCommand.move_joint((0.0,) * 6))
    assert uncertain.status is not None
    backend_calls = tuple(backend.calls)
    locked = robot.motion_locked
    robot.disconnect()
    return {
        "status": "SOFTWARE_VALIDATED",
        "hardware_validation": False,
        "max_hardware_validation_level": 0,
        "uncertain_status": uncertain.status.value,
        "motion_locked_after_reconnect": locked,
        "reconnect_synchronized": reconnect.success,
        "blocked_error_code": blocked.error_code,
        "automatic_motion_resume_observed": any("resume" in call for call in backend_calls),
        "application_fault_event_state": events[-1].state.value,
        "application_fault_event_type": events[-1].event_type,
    }


def run_replay_demo(journal_path: Path) -> dict[str, object]:
    replay = ReplayRobot(journal_path)
    connected = replay.connect()
    result = {
        "status": "REPLAY_READY",
        "hardware_validation": False,
        "max_hardware_validation_level": 0,
        "connected": connected.success,
        "remaining_command_results": replay.remaining,
        "capabilities": sorted(capability.value for capability in replay.capabilities),
        "journal": str(journal_path),
    }
    replay.disconnect()
    return result
