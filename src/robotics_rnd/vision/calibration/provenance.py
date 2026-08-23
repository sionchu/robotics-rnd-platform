"""Calibration provenance and camera-configuration binding."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from robotics_rnd.vision.camera import ImageSize
from robotics_rnd.vision.dataset import GroundTruthClass

from .io import calibration_from_dict, calibration_to_dict
from .models import CameraCalibrationResult


@dataclass(frozen=True, slots=True)
class CameraConfigurationBinding:
    sensor_model: str
    camera_mode: str
    capture_size: ImageSize
    calibration_size: ImageSize
    pixel_format: str
    scaler_crop: tuple[int, int, int, int] | None = None

    def __post_init__(self) -> None:
        if not self.sensor_model.strip() or not self.camera_mode.strip() or not self.pixel_format.strip():
            raise ValueError("sensor, camera mode, and pixel format are required")
        if self.scaler_crop is not None:
            crop = tuple(int(value) for value in self.scaler_crop)
            if len(crop) != 4 or crop[2] <= 0 or crop[3] <= 0:
                raise ValueError("scaler crop must contain x, y, positive width, and positive height")
            object.__setattr__(self, "scaler_crop", crop)

    def assert_compatible(
        self,
        *,
        sensor_model: str,
        camera_mode: str,
        capture_size: ImageSize,
        pixel_format: str,
        scaler_crop: tuple[int, int, int, int] | None = None,
    ) -> None:
        expected = (
            self.sensor_model,
            self.camera_mode,
            self.capture_size,
            self.pixel_format,
            self.scaler_crop,
        )
        observed = (sensor_model, camera_mode, capture_size, pixel_format, scaler_crop)
        if observed != expected:
            raise ValueError("camera configuration does not match calibration provenance")


@dataclass(frozen=True, slots=True)
class CalibrationArtifact:
    calibration: CameraCalibrationResult
    binding: CameraConfigurationBinding
    dataset_id: str
    ground_truth_class: GroundTruthClass
    measurement_uncertainty: str
    software_versions: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.calibration.intrinsics.image_size != self.binding.calibration_size:
            raise ValueError("calibration image size does not match provenance binding")
        if not self.dataset_id.strip() or not self.measurement_uncertainty.strip():
            raise ValueError("calibration dataset and uncertainty statement are required")
        object.__setattr__(self, "software_versions", MappingProxyType(dict(self.software_versions)))

    def to_dict(self) -> dict[str, Any]:
        binding = self.binding
        return {
            "schema": "robotics-rnd-calibration-artifact-v1",
            "calibration": calibration_to_dict(self.calibration),
            "binding": {
                "sensor_model": binding.sensor_model,
                "camera_mode": binding.camera_mode,
                "capture_size_px": {
                    "width": binding.capture_size.width_px,
                    "height": binding.capture_size.height_px,
                },
                "calibration_size_px": {
                    "width": binding.calibration_size.width_px,
                    "height": binding.calibration_size.height_px,
                },
                "pixel_format": binding.pixel_format,
                "scaler_crop": list(binding.scaler_crop) if binding.scaler_crop is not None else None,
            },
            "dataset_id": self.dataset_id,
            "ground_truth_class": self.ground_truth_class.value,
            "measurement_uncertainty": self.measurement_uncertainty,
            "software_versions": dict(self.software_versions),
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> CalibrationArtifact:
        if document.get("schema") != "robotics-rnd-calibration-artifact-v1":
            raise ValueError("unsupported calibration artifact schema")
        binding = document["binding"]
        capture_size = binding["capture_size_px"]
        calibration_size = binding["calibration_size_px"]
        return cls(
            calibration=calibration_from_dict(dict(document["calibration"])),
            binding=CameraConfigurationBinding(
                sensor_model=str(binding["sensor_model"]),
                camera_mode=str(binding["camera_mode"]),
                capture_size=ImageSize(int(capture_size["width"]), int(capture_size["height"])),
                calibration_size=ImageSize(int(calibration_size["width"]), int(calibration_size["height"])),
                pixel_format=str(binding["pixel_format"]),
                scaler_crop=(tuple(binding["scaler_crop"]) if binding.get("scaler_crop") else None),
            ),
            dataset_id=str(document["dataset_id"]),
            ground_truth_class=GroundTruthClass(str(document["ground_truth_class"])),
            measurement_uncertainty=str(document["measurement_uncertainty"]),
            software_versions=document.get("software_versions", {}),
        )


def save_calibration_artifact(artifact: CalibrationArtifact, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_calibration_artifact(path: Path) -> CalibrationArtifact:
    return CalibrationArtifact.from_dict(json.loads(path.read_text(encoding="utf-8")))
