"""Calibration outputs; algorithms and vendor solvers remain external."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from robotics_rnd.core import QualityMetric
from robotics_rnd.core.geometry import Transform


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    transform: Transform
    method: str
    validated: bool = False
    quality: tuple[QualityMetric, ...] = ()
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.method.strip():
            raise ValueError("calibration method is required")
        if self.created_at.tzinfo is None:
            raise ValueError("calibration timestamp must be timezone-aware")
