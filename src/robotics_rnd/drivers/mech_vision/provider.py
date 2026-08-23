"""External vision-result provider boundary, distinct from direct camera capture."""

from __future__ import annotations

from robotics_rnd.vision import VisionCapability, VisionInterface, VisionObservation


class MechVisionProvider(VisionInterface):
    @property
    def capabilities(self) -> frozenset[VisionCapability]:
        return frozenset()

    def observe(self) -> VisionObservation:
        raise RuntimeError(
            "Mech-Vision provider is unavailable. Configure and validate the supported Standard "
            "Interface separately before adding a platform mapping."
        )
