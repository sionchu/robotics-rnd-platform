"""Portable camera capabilities and capture metadata."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any

from .models import ImageSize


def _optional_non_negative(value: float | None, name: str) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


@dataclass(frozen=True, slots=True)
class CameraCapabilities:
    """Hardware-neutral capability summary discovered by an adapter."""

    sensor_model: str | None = None
    modes: tuple[str, ...] = ()
    pixel_formats: tuple[str, ...] = ()
    controls: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if self.sensor_model is not None and not self.sensor_model.strip():
            raise ValueError("camera sensor model cannot be blank")
        if any(not item.strip() for item in (*self.modes, *self.pixel_formats, *self.controls)):
            raise ValueError("camera capability names cannot be blank")


@dataclass(frozen=True, slots=True)
class CaptureMetadata:
    """Normalized metadata for one image, without camera-library objects."""

    sequence_index: int
    monotonic_timestamp_ns: int
    capture_size: ImageSize
    pixel_format: str
    sensor_timestamp_ns: int | None = None
    exposure_time_us: float | None = None
    analogue_gain: float | None = None
    digital_gain: float | None = None
    colour_gains: tuple[float, float] | None = None
    lens_position: float | None = None
    frame_duration_us: float | None = None
    scaler_crop: tuple[int, int, int, int] | None = None
    extra: Mapping[str, str | int | float | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.sequence_index < 0 or self.monotonic_timestamp_ns < 0:
            raise ValueError("capture sequence and monotonic timestamp must be non-negative")
        if not self.pixel_format.strip():
            raise ValueError("capture pixel format is required")
        if self.sensor_timestamp_ns is not None and self.sensor_timestamp_ns < 0:
            raise ValueError("sensor timestamp must be non-negative")
        for name in (
            "exposure_time_us",
            "analogue_gain",
            "digital_gain",
            "lens_position",
            "frame_duration_us",
        ):
            object.__setattr__(self, name, _optional_non_negative(getattr(self, name), name))
        if self.colour_gains is not None:
            gains = tuple(float(value) for value in self.colour_gains)
            if len(gains) != 2 or not all(isfinite(value) and value >= 0.0 for value in gains):
                raise ValueError("colour gains must contain two finite non-negative values")
            object.__setattr__(self, "colour_gains", gains)
        if self.scaler_crop is not None:
            crop = tuple(int(value) for value in self.scaler_crop)
            if len(crop) != 4 or any(value < 0 for value in crop) or crop[2] <= 0 or crop[3] <= 0:
                raise ValueError("scaler crop must be non-negative x/y and positive width/height")
            object.__setattr__(self, "scaler_crop", crop)
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "robotics-rnd-capture-metadata-v1",
            "sequence_index": self.sequence_index,
            "monotonic_timestamp_ns": self.monotonic_timestamp_ns,
            "sensor_timestamp_ns": self.sensor_timestamp_ns,
            "capture_size_px": {
                "width": self.capture_size.width_px,
                "height": self.capture_size.height_px,
            },
            "pixel_format": self.pixel_format,
            "exposure_time_us": self.exposure_time_us,
            "analogue_gain": self.analogue_gain,
            "digital_gain": self.digital_gain,
            "colour_gains": list(self.colour_gains) if self.colour_gains is not None else None,
            "lens_position": self.lens_position,
            "frame_duration_us": self.frame_duration_us,
            "scaler_crop": list(self.scaler_crop) if self.scaler_crop is not None else None,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> CaptureMetadata:
        if document.get("schema") != "robotics-rnd-capture-metadata-v1":
            raise ValueError("unsupported capture metadata schema")
        size = document["capture_size_px"]
        return cls(
            sequence_index=int(document["sequence_index"]),
            monotonic_timestamp_ns=int(document["monotonic_timestamp_ns"]),
            sensor_timestamp_ns=(
                int(document["sensor_timestamp_ns"])
                if document.get("sensor_timestamp_ns") is not None
                else None
            ),
            capture_size=ImageSize(int(size["width"]), int(size["height"])),
            pixel_format=str(document["pixel_format"]),
            exposure_time_us=document.get("exposure_time_us"),
            analogue_gain=document.get("analogue_gain"),
            digital_gain=document.get("digital_gain"),
            colour_gains=(
                tuple(document["colour_gains"]) if document.get("colour_gains") is not None else None
            ),
            lens_position=document.get("lens_position"),
            frame_duration_us=document.get("frame_duration_us"),
            scaler_crop=(tuple(document["scaler_crop"]) if document.get("scaler_crop") is not None else None),
            extra=document.get("extra", {}),
        )
