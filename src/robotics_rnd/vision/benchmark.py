"""Portable benchmark records for CPU, GPU, and future edge comparisons."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any

from robotics_rnd.vision.camera import ImageSize


@dataclass(frozen=True, slots=True)
class VisionBenchmarkResult:
    host: str
    cpu: str
    gpu: str | None
    source_type: str
    image_size: ImageSize
    algorithm: str
    latency_ms: float
    fps: float
    success_rate: float
    memory_mb: float | None = None
    accuracy_metrics: Mapping[str, float] = field(default_factory=dict)
    software_versions: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = (self.host, self.cpu, self.source_type, self.algorithm)
        if any(not value.strip() for value in required):
            raise ValueError("benchmark host, CPU, source type, and algorithm are required")
        if not isfinite(self.latency_ms) or self.latency_ms < 0.0:
            raise ValueError("benchmark latency must be finite non-negative milliseconds")
        if not isfinite(self.fps) or self.fps < 0.0:
            raise ValueError("benchmark FPS must be finite and non-negative")
        if not isfinite(self.success_rate) or not 0.0 <= self.success_rate <= 1.0:
            raise ValueError("benchmark success rate must be in [0, 1]")
        if self.memory_mb is not None and (not isfinite(self.memory_mb) or self.memory_mb < 0.0):
            raise ValueError("benchmark memory must be finite non-negative megabytes")
        if not all(isfinite(value) for value in self.accuracy_metrics.values()):
            raise ValueError("benchmark accuracy metrics must be finite")
        object.__setattr__(self, "accuracy_metrics", MappingProxyType(dict(self.accuracy_metrics)))
        object.__setattr__(self, "software_versions", MappingProxyType(dict(self.software_versions)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "cpu": self.cpu,
            "gpu": self.gpu,
            "source_type": self.source_type,
            "image_resolution": {
                "width_px": self.image_size.width_px,
                "height_px": self.image_size.height_px,
            },
            "algorithm": self.algorithm,
            "latency_ms": self.latency_ms,
            "fps": self.fps,
            "memory_mb": self.memory_mb,
            "success_rate": self.success_rate,
            "accuracy_metrics": dict(self.accuracy_metrics),
            "software_versions": dict(self.software_versions),
        }
