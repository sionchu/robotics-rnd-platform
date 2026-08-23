"""Small vision-to-robot job proving interface-only composition."""

from __future__ import annotations

from dataclasses import dataclass

from robotics_rnd.core.geometry import Transform
from robotics_rnd.core.state_machine import JobEvent, JobState, build_job_state_machine
from robotics_rnd.robot import RobotCommand, RobotInterface, RobotResult
from robotics_rnd.vision import VisionInterface, VisionObservation


@dataclass(frozen=True, slots=True)
class GuidanceRun:
    observation: VisionObservation
    robot_result: RobotResult
    final_state: JobState


class MockGuidanceJob:
    """One-shot guidance example; no retry, path planning, or safety claim."""

    def __init__(
        self,
        robot: RobotInterface,
        vision: VisionInterface,
        camera_to_base: Transform,
    ) -> None:
        self.robot = robot
        self.vision = vision
        self.camera_to_base = camera_to_base
        self.machine = build_job_state_machine()

    def run(self) -> GuidanceRun:
        try:
            self.machine.trigger(JobEvent.CONNECT)
            self.robot.connect()
            self.machine.trigger(JobEvent.CONNECTION_READY)
            self.machine.trigger(JobEvent.START)
            observation = self.vision.observe()
            if not observation.targets:
                raise RuntimeError("vision observation contains no target")
            target_in_base = self.camera_to_base.transform_pose(observation.targets[0].pose)
            result = self.robot.execute(RobotCommand.move_linear(target_in_base))
            if not result.success:
                raise RuntimeError(result.message)
            self.machine.trigger(JobEvent.SUCCEED)
            return GuidanceRun(observation, result, self.machine.state)
        except Exception:
            if self.machine.can_trigger(JobEvent.FAIL):
                self.machine.trigger(JobEvent.FAIL)
            raise
