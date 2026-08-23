"""Validated configuration for the optional Picamera2 adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from robotics_rnd.core import FrameId
from robotics_rnd.vision.camera import ImageSize


class PiCameraControlMode(StrEnum):
    AUTO = "AUTO"
    CONTROLLED = "CONTROLLED"


class PiCameraLifecycle(StrEnum):
    NEW = "NEW"
    OPEN = "OPEN"
    CONFIGURED = "CONFIGURED"
    STARTED = "STARTED"
    STOPPED = "STOPPED"
    CLOSED = "CLOSED"


@dataclass(frozen=True, slots=True)
class PiCameraConfig:
    image_size: ImageSize
    pixel_format: str = "BGR888"
    camera_index: int = 0
    warmup_frames: int = 20
    frame_id: FrameId = field(default_factory=lambda: FrameId("pi_camera"))
    source_id: str = "pi-camera"
    control_mode: PiCameraControlMode = PiCameraControlMode.AUTO
    controls: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.pixel_format not in {"BGR888", "RGB888"}:
            raise ValueError("Pi camera pixel format must be BGR888 or RGB888")
        if self.camera_index < 0 or self.warmup_frames < 0:
            raise ValueError("camera index and warm-up frame count must be non-negative")
        if not self.source_id.strip():
            raise ValueError("Pi camera source id is required")
        controls = dict(self.controls)
        if any(not str(name).strip() for name in controls):
            raise ValueError("camera control names cannot be blank")
        object.__setattr__(self, "controls", MappingProxyType(controls))

    def requested_controls(self) -> dict[str, Any]:
        return dict(self.controls)
