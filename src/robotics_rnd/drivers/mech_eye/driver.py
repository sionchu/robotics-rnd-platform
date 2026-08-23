"""Direct-camera adapter boundary; vendor SDK code is intentionally absent."""

from __future__ import annotations

from robotics_rnd.vision import VisionCapability, VisionInterface, VisionObservation


class MechEyeDriver(VisionInterface):
    @property
    def capabilities(self) -> frozenset[VisionCapability]:
        return frozenset()

    def observe(self) -> VisionObservation:
        raise RuntimeError(
            "Mech-Eye adapter is unavailable. Install the official SDK separately and implement "
            "a reviewed direct-camera mapping without exposing SDK objects."
        )
