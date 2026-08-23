"""Picamera2 adapter with lazy imports and platform-owned frame output."""

from __future__ import annotations

import platform
from collections.abc import Mapping
from datetime import UTC, datetime
from importlib import import_module
from time import monotonic_ns
from typing import Any, Protocol, cast

import numpy as np

from robotics_rnd.vision.camera import CameraCapabilities, CaptureMetadata, ImageFrame

from .models import PiCameraConfig, PiCameraControlMode, PiCameraLifecycle


class PiCameraUnavailable(RuntimeError):
    pass


class PiCameraLifecycleError(RuntimeError):
    pass


class UnsupportedCameraControl(ValueError):
    pass


class CapturedRequest(Protocol):
    def make_array(self, name: str) -> np.ndarray: ...

    def get_metadata(self) -> Mapping[str, Any]: ...

    def release(self) -> None: ...


class CameraBackend(Protocol):
    camera_controls: Mapping[str, Any]
    sensor_modes: list[Mapping[str, Any]]

    def create_video_configuration(self, *, main: Mapping[str, Any], controls: Mapping[str, Any]) -> Any: ...

    def configure(self, configuration: Any) -> None: ...

    def start(self) -> None: ...

    def capture_request(self) -> CapturedRequest: ...

    def set_controls(self, controls: Mapping[str, Any]) -> None: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...


def _default_backend(camera_index: int) -> CameraBackend:
    if platform.machine().lower() not in {"aarch64", "arm64"}:
        raise PiCameraUnavailable(
            "Picamera2 hardware access requires Raspberry Pi ARM64; use replay on this platform"
        )
    try:
        module = import_module("picamera2")
    except ImportError as exc:
        raise PiCameraUnavailable(
            "Picamera2 is unavailable. On supported Raspberry Pi OS install the vendor package "
            "python3-picamera2, then rerun the Pi doctor."
        ) from exc
    picamera2_type = getattr(module, "Picamera2", None)
    if picamera2_type is None:
        raise PiCameraUnavailable("the installed picamera2 module does not expose Picamera2")
    return cast(CameraBackend, picamera2_type(camera_index))


def _number(metadata: Mapping[str, Any], key: str) -> float | None:
    value = metadata.get(key)
    return float(value) if isinstance(value, int | float) else None


def normalize_picamera2_metadata(
    metadata: Mapping[str, Any],
    config: PiCameraConfig,
    *,
    sequence_index: int,
    receive_timestamp_ns: int,
) -> CaptureMetadata:
    """Map documented Picamera2 keys to portable values and discard SDK objects."""

    colour_gains_raw = metadata.get("ColourGains")
    colour_gains: tuple[float, float] | None = None
    if isinstance(colour_gains_raw, list | tuple) and len(colour_gains_raw) == 2:
        colour_gains = (float(colour_gains_raw[0]), float(colour_gains_raw[1]))
    crop_raw = metadata.get("ScalerCrop")
    scaler_crop: tuple[int, int, int, int] | None = None
    if isinstance(crop_raw, list | tuple) and len(crop_raw) == 4:
        scaler_crop = (
            int(crop_raw[0]),
            int(crop_raw[1]),
            int(crop_raw[2]),
            int(crop_raw[3]),
        )
    sensor_timestamp = metadata.get("SensorTimestamp")
    safe_extra: dict[str, str | int | float | bool | None] = {}
    for key in ("Lux", "ColourTemperature", "FocusFoM"):
        value = metadata.get(key)
        if isinstance(value, str | int | float | bool) or value is None:
            safe_extra[key] = value
    return CaptureMetadata(
        sequence_index=sequence_index,
        monotonic_timestamp_ns=receive_timestamp_ns,
        sensor_timestamp_ns=(int(sensor_timestamp) if isinstance(sensor_timestamp, int) else None),
        capture_size=config.image_size,
        pixel_format=config.pixel_format,
        exposure_time_us=_number(metadata, "ExposureTime"),
        analogue_gain=_number(metadata, "AnalogueGain"),
        digital_gain=_number(metadata, "DigitalGain"),
        colour_gains=colour_gains,
        lens_position=_number(metadata, "LensPosition"),
        frame_duration_us=_number(metadata, "FrameDuration"),
        scaler_crop=scaler_crop,
        extra=safe_extra,
    )


class PiCameraSource:
    """Lifecycle-controlled Picamera2 source; Picamera2 values never escape it."""

    def __init__(self, config: PiCameraConfig, backend: CameraBackend | None = None) -> None:
        self.config = config
        self._backend = backend
        self._state = PiCameraLifecycle.NEW
        self._sequence_index = 0
        self._last_warmup_metadata: CaptureMetadata | None = None

    @property
    def lifecycle(self) -> PiCameraLifecycle:
        return self._state

    @property
    def last_warmup_metadata(self) -> CaptureMetadata | None:
        return self._last_warmup_metadata

    @property
    def capabilities(self) -> CameraCapabilities:
        if self._backend is None or self._state is PiCameraLifecycle.NEW:
            raise PiCameraLifecycleError("open the camera before reading capabilities")
        modes = tuple(str(dict(mode)) for mode in self._backend.sensor_modes)
        formats = tuple(
            sorted(
                {
                    str(mode["format"])
                    for mode in self._backend.sensor_modes
                    if isinstance(mode, Mapping) and "format" in mode
                }
            )
        )
        return CameraCapabilities(
            modes=modes,
            pixel_formats=formats,
            controls=frozenset(str(name) for name in self._backend.camera_controls),
        )

    def open(self) -> None:
        if self._state is not PiCameraLifecycle.NEW:
            raise PiCameraLifecycleError(f"cannot open camera from {self._state}")
        if self._backend is None:
            self._backend = _default_backend(self.config.camera_index)
        self._state = PiCameraLifecycle.OPEN

    def _require_backend(self) -> CameraBackend:
        if self._backend is None:
            raise PiCameraLifecycleError("camera backend is not open")
        return self._backend

    def _validate_controls(self, controls: Mapping[str, Any]) -> None:
        supported = self._require_backend().camera_controls
        unsupported = sorted(set(controls) - set(supported))
        if unsupported:
            raise UnsupportedCameraControl(f"unsupported camera controls: {unsupported}")

    def configure(self) -> None:
        if self._state is not PiCameraLifecycle.OPEN:
            raise PiCameraLifecycleError(f"cannot configure camera from {self._state}")
        backend = self._require_backend()
        controls = self.config.requested_controls()
        self._validate_controls(controls)
        if self.config.control_mode is PiCameraControlMode.AUTO:
            for name in ("AeEnable", "AwbEnable"):
                if name in backend.camera_controls:
                    controls.setdefault(name, True)
        configuration = backend.create_video_configuration(
            main={
                "size": (self.config.image_size.width_px, self.config.image_size.height_px),
                "format": self.config.pixel_format,
            },
            controls=controls,
        )
        backend.configure(configuration)
        self._state = PiCameraLifecycle.CONFIGURED

    def _capture(self, sequence_index: int) -> tuple[np.ndarray, CaptureMetadata]:
        backend = self._require_backend()
        request = backend.capture_request()
        receive_timestamp = monotonic_ns()
        try:
            image = np.asarray(request.make_array("main"), dtype=np.uint8)
            metadata = normalize_picamera2_metadata(
                request.get_metadata(),
                self.config,
                sequence_index=sequence_index,
                receive_timestamp_ns=receive_timestamp,
            )
        finally:
            request.release()
        return image, metadata

    def start(self) -> None:
        if self._state not in {PiCameraLifecycle.CONFIGURED, PiCameraLifecycle.STOPPED}:
            raise PiCameraLifecycleError(f"cannot start camera from {self._state}")
        backend = self._require_backend()
        backend.start()
        self._state = PiCameraLifecycle.STARTED
        for index in range(self.config.warmup_frames):
            _image, metadata = self._capture(index)
            self._last_warmup_metadata = metadata

    def set_controls(self, controls: Mapping[str, Any]) -> None:
        if self._state is not PiCameraLifecycle.STARTED:
            raise PiCameraLifecycleError("camera controls can be changed only while started")
        self._validate_controls(controls)
        self._require_backend().set_controls(dict(controls))

    def read(self) -> ImageFrame:
        if self._state is not PiCameraLifecycle.STARTED:
            raise PiCameraLifecycleError("camera must be started before capture")
        image, metadata = self._capture(self._sequence_index)
        frame = ImageFrame(
            frame_id=self.config.frame_id,
            timestamp=datetime.now(UTC),
            image=image,
            source_id=self.config.source_id,
            capture_metadata=metadata,
        )
        self._sequence_index += 1
        return frame

    def stop(self) -> None:
        if self._state is not PiCameraLifecycle.STARTED:
            raise PiCameraLifecycleError(f"cannot stop camera from {self._state}")
        self._require_backend().stop()
        self._state = PiCameraLifecycle.STOPPED

    def close(self) -> None:
        if self._state is PiCameraLifecycle.STARTED:
            self.stop()
        if self._state in {PiCameraLifecycle.NEW, PiCameraLifecycle.CLOSED}:
            raise PiCameraLifecycleError(f"cannot close camera from {self._state}")
        self._require_backend().close()
        self._state = PiCameraLifecycle.CLOSED

    def __enter__(self) -> PiCameraSource:
        self.open()
        self.configure()
        self.start()
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        if self._state is not PiCameraLifecycle.CLOSED:
            self.close()
