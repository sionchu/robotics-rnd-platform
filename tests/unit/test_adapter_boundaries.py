import pytest

from robotics_rnd.drivers.mech_eye import MechEyeDriver
from robotics_rnd.drivers.mech_vision import MechVisionProvider
from robotics_rnd.drivers.rainbow import RainbowRobotDriver
from robotics_rnd.robot.errors import DriverUnavailable


def test_rainbow_skeleton_fails_actionably_without_claiming_capabilities() -> None:
    driver = RainbowRobotDriver()
    assert driver.capabilities == frozenset()
    with pytest.raises(DriverUnavailable, match="rbpodo"):
        driver.connect()


@pytest.mark.parametrize("provider", [MechEyeDriver(), MechVisionProvider()])
def test_vision_vendor_stubs_are_distinct_and_fail_actionably(provider) -> None:
    assert provider.capabilities == frozenset()
    with pytest.raises(RuntimeError, match="unavailable"):
        provider.observe()
