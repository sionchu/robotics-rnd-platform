"""In-memory deterministic replay independent of vendor file formats."""

from __future__ import annotations

from robotics_rnd.vision import VisionCapability, VisionInterface, VisionObservation


class ReplayVision(VisionInterface):
    def __init__(self, observations: tuple[VisionObservation, ...]) -> None:
        if not observations:
            raise ValueError("replay requires at least one observation")
        self._observations = observations
        self._cursor = 0

    @property
    def capabilities(self) -> frozenset[VisionCapability]:
        return frozenset({VisionCapability.TARGET_POSE})

    @property
    def remaining(self) -> int:
        return len(self._observations) - self._cursor

    def reset(self) -> None:
        self._cursor = 0

    def observe(self) -> VisionObservation:
        if self._cursor >= len(self._observations):
            raise StopIteration("replay observations exhausted")
        result = self._observations[self._cursor]
        self._cursor += 1
        return result
