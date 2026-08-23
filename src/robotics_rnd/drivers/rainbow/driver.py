"""Safe Rainbow Robotics boundary; no live mapping is claimed at bootstrap."""

from __future__ import annotations

from robotics_rnd.robot import RobotCapability, RobotCommand, RobotInterface, RobotResult, RobotState
from robotics_rnd.robot.errors import DriverUnavailable


class RainbowRobotDriver(RobotInterface):
    """Explicit skeleton for a future independently validated `rbpodo` adapter."""

    _MESSAGE = (
        "Rainbow adapter is not configured. Install a compatible rbpodo release separately, "
        "validate controller/SDK versions and safety policy, then implement mappings in this driver."
    )

    @property
    def capabilities(self) -> frozenset[RobotCapability]:
        return frozenset()

    def connect(self) -> RobotResult:
        raise DriverUnavailable(self._MESSAGE)

    def disconnect(self) -> RobotResult:
        raise DriverUnavailable(self._MESSAGE)

    def get_state(self) -> RobotState:
        raise DriverUnavailable(self._MESSAGE)

    def execute(self, command: RobotCommand) -> RobotResult:
        raise DriverUnavailable(self._MESSAGE)

    def stop(self) -> RobotResult:
        raise DriverUnavailable(self._MESSAGE)

    def reset_fault(self) -> RobotResult:
        raise DriverUnavailable(self._MESSAGE)
