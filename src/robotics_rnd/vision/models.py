"""Vendor-neutral vision observations with explicit timestamps and frames."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any

from robotics_rnd.core import FrameId, QualityMetric
from robotics_rnd.core.geometry import Pose


@dataclass(frozen=True, slots=True)
class VisionTarget:
    target_id: str
    pose: Pose
    confidence: float
    quality: tuple[QualityMetric, ...] = ()

    def __post_init__(self) -> None:
        if not self.target_id.strip():
            raise ValueError("vision target id is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("vision confidence must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class VisionObservation:
    observation_id: str
    timestamp: datetime
    frame_id: FrameId
    targets: tuple[VisionTarget, ...] = ()
    quality: tuple[QualityMetric, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("vision observation id is required")
        if self.timestamp.tzinfo is None:
            raise ValueError("vision timestamp must be timezone-aware")
        if any(target.pose.frame != self.frame_id for target in self.targets):
            raise ValueError("all target poses must be expressed in the observation frame")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
