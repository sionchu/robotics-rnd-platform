"""Robot boundary exceptions."""


class RobotError(RuntimeError):
    pass


class RobotNotConnected(RobotError):
    pass


class RobotFault(RobotError):
    pass


class UnsupportedRobotCapability(RobotError):
    pass


class DriverUnavailable(RobotError):
    pass
