import pytest

from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Pose, Quaternion, Vector3
from robotics_rnd.drivers.mock import MockRobot
from robotics_rnd.robot import RobotCommand, RobotMode
from robotics_rnd.robot.errors import RobotFault, RobotNotConnected


def test_connect_disconnect_and_state_transition() -> None:
    robot = MockRobot()
    assert robot.get_state().mode is RobotMode.DISCONNECTED
    assert robot.connect().state.mode is RobotMode.IDLE
    assert robot.disconnect().state.mode is RobotMode.DISCONNECTED


def test_command_while_disconnected_is_rejected() -> None:
    robot = MockRobot()
    with pytest.raises(RobotNotConnected):
        robot.execute(RobotCommand.move_joint((0.0,) * 6))


def test_joint_and_pose_targets_are_deterministic() -> None:
    base = FrameId("robot_base")
    robot = MockRobot(base_frame=base)
    robot.connect()
    joint_result = robot.execute(RobotCommand.move_joint((0.1, 0.2, 0.3, 0.4, 0.5, 0.6)))
    assert joint_result.command_id == "mock-0001"
    assert joint_result.state.joints.positions_rad[-1] == 0.6
    pose = Pose(Vector3(0.2, 0.1, 0.3), Quaternion.identity(), base)
    pose_result = robot.execute(RobotCommand.move_linear(pose))
    assert pose_result.command_id == "mock-0002"
    assert pose_result.state.tool_pose == pose


def test_stop_fault_and_reset_paths() -> None:
    robot = MockRobot()
    robot.connect()
    assert robot.stop().state.mode is RobotMode.STOPPED
    assert robot.inject_fault("test fault").mode is RobotMode.FAULT
    with pytest.raises(RobotFault, match="test fault"):
        robot.execute(RobotCommand.move_joint((0.0,) * 6))
    assert robot.reset_fault().state.mode is RobotMode.IDLE


def test_wrong_joint_count_and_frame_are_rejected() -> None:
    robot = MockRobot()
    robot.connect()
    with pytest.raises(ValueError, match="count"):
        robot.execute(RobotCommand.move_joint((0.0,)))
    wrong_pose = Pose.identity(FrameId("camera"))
    with pytest.raises(ValueError, match="robot_base"):
        robot.execute(RobotCommand.move_linear(wrong_pose))
