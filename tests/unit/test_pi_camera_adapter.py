from __future__ import annotations

import platform
from collections.abc import Mapping
from typing import Any, ClassVar

import numpy as np
import pytest

from robotics_rnd.drivers.raspberry_pi import PiCameraConfig, PiCameraLifecycle, PiCameraSource
from robotics_rnd.drivers.raspberry_pi.camera import (
    PiCameraLifecycleError,
    PiCameraUnavailable,
    UnsupportedCameraControl,
)
from robotics_rnd.vision.camera import ImageSize


class FakeRequest:
    def __init__(self, index: int, size: ImageSize) -> None:
        self.index = index
        self.size = size
        self.released = False

    def make_array(self, name: str) -> np.ndarray:
        assert name == "main"
        return np.full((*self.size.shape, 3), self.index, dtype=np.uint8)

    def get_metadata(self) -> Mapping[str, Any]:
        return {
            "SensorTimestamp": 1_000_000 + self.index,
            "ExposureTime": 5_000,
            "AnalogueGain": 1.5,
            "DigitalGain": 1.0,
            "ColourGains": (1.2, 1.4),
            "LensPosition": 2.0,
            "FrameDuration": 33_333,
            "ScalerCrop": (0, 0, self.size.width_px, self.size.height_px),
            "Lux": 100.0,
            "private_sdk_object": object(),
        }

    def release(self) -> None:
        self.released = True


class FakeBackend:
    camera_controls: ClassVar[dict[str, Any]] = {
        "AeEnable": None,
        "AwbEnable": None,
        "ExposureTime": None,
        "AnalogueGain": None,
    }
    sensor_modes: ClassVar[list[Mapping[str, Any]]] = [{"format": "SRGGB10_CSI2P", "size": (640, 480)}]

    def __init__(self, size: ImageSize) -> None:
        self.size = size
        self.configuration: Any = None
        self.started = False
        self.closed = False
        self.requests: list[FakeRequest] = []
        self.controls: dict[str, Any] = {}

    def create_video_configuration(
        self, *, main: Mapping[str, Any], controls: Mapping[str, Any]
    ) -> dict[str, Any]:
        return {"main": dict(main), "controls": dict(controls)}

    def configure(self, configuration: Any) -> None:
        self.configuration = configuration

    def start(self) -> None:
        self.started = True

    def capture_request(self) -> FakeRequest:
        request = FakeRequest(len(self.requests), self.size)
        self.requests.append(request)
        return request

    def set_controls(self, controls: Mapping[str, Any]) -> None:
        self.controls.update(controls)

    def stop(self) -> None:
        self.started = False

    def close(self) -> None:
        self.closed = True


def test_pi_adapter_lifecycle_metadata_and_no_sdk_object_leak() -> None:
    size = ImageSize(64, 48)
    backend = FakeBackend(size)
    config = PiCameraConfig(size, warmup_frames=2)
    source = PiCameraSource(config, backend)
    source.open()
    assert source.lifecycle is PiCameraLifecycle.OPEN
    assert source.capabilities.controls == frozenset(backend.camera_controls)
    source.configure()
    source.start()
    assert source.last_warmup_metadata is not None
    frame = source.read()
    assert frame.image_size == size
    assert frame.capture_metadata is not None
    assert frame.capture_metadata.sequence_index == 0
    assert frame.capture_metadata.exposure_time_us == 5_000
    assert frame.capture_metadata.extra == {"Lux": 100.0, "ColourTemperature": None, "FocusFoM": None}
    assert "private_sdk_object" not in str(frame.capture_metadata.to_dict())
    assert all(request.released for request in backend.requests)
    source.stop()
    source.close()
    assert source.lifecycle is PiCameraLifecycle.CLOSED
    assert backend.closed is True


def test_pi_adapter_rejects_unsupported_controls_and_invalid_lifecycle() -> None:
    size = ImageSize(64, 48)
    source = PiCameraSource(PiCameraConfig(size, controls={"Unsupported": 1}), FakeBackend(size))
    with pytest.raises(PiCameraLifecycleError, match="started"):
        source.read()
    source.open()
    with pytest.raises(UnsupportedCameraControl, match="Unsupported"):
        source.configure()


def test_native_backend_is_unavailable_off_pi() -> None:
    if platform.machine().lower() in {"aarch64", "arm64"}:
        pytest.skip("unsupported-platform path is specific to non-ARM CI")
    source = PiCameraSource(PiCameraConfig(ImageSize(64, 48)))
    with pytest.raises(PiCameraUnavailable, match="ARM64"):
        source.open()
