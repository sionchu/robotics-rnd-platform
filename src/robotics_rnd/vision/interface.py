"""Vision provider boundary."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum

from .models import VisionObservation


class VisionCapability(StrEnum):
    TARGET_POSE = "TARGET_POSE"
    IMAGE_2D = "IMAGE_2D"
    DEPTH = "DEPTH"
    POINT_CLOUD = "POINT_CLOUD"


class VisionInterface(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> frozenset[VisionCapability]:
        raise NotImplementedError

    @abstractmethod
    def observe(self) -> VisionObservation:
        raise NotImplementedError
