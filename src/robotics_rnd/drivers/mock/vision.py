"""Deterministic vision provider for contract and workflow tests."""

from __future__ import annotations

from robotics_rnd.vision import VisionCapability, VisionInterface, VisionObservation


class MockVision(VisionInterface):
    def __init__(self, observations: tuple[VisionObservation, ...], repeat_last: bool = True) -> None:
        if not observations:
            raise ValueError("mock vision requires at least one observation")
        self._observations = observations
        self._repeat_last = repeat_last
        self._index = 0

    @property
    def capabilities(self) -> frozenset[VisionCapability]:
        return frozenset({VisionCapability.TARGET_POSE})

    def observe(self) -> VisionObservation:
        if self._index >= len(self._observations):
            if self._repeat_last:
                return self._observations[-1]
            raise StopIteration("mock vision observations exhausted")
        result = self._observations[self._index]
        self._index += 1
        return result
