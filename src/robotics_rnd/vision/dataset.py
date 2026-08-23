"""Auditable capture-dataset manifests and deterministic image replay."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any

import cv2
import numpy as np

from robotics_rnd.core import FrameId
from robotics_rnd.vision.camera import CaptureMetadata, ImageFrame, ImageSize

_SESSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")


class GroundTruthClass(StrEnum):
    ALGORITHM_GROUND_TRUTH = "ALGORITHM_GROUND_TRUTH"
    SYNTHETIC_GROUND_TRUTH = "SYNTHETIC_GROUND_TRUTH"
    MEASURED_PHYSICAL_REFERENCE = "MEASURED_PHYSICAL_REFERENCE"
    NOMINAL_PHYSICAL_REFERENCE = "NOMINAL_PHYSICAL_REFERENCE"
    NO_GROUND_TRUTH_REPEATABILITY_ONLY = "NO_GROUND_TRUTH_REPEATABILITY_ONLY"


def _safe_relative_path(value: str, name: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"{name} must be a safe relative path")
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class DatasetFrameRecord:
    sequence_index: int
    captured_at: datetime
    image_path: str
    metadata_path: str

    def __post_init__(self) -> None:
        if self.sequence_index < 0:
            raise ValueError("dataset frame sequence must be non-negative")
        if self.captured_at.tzinfo is None:
            raise ValueError("dataset frame timestamp must be timezone-aware")
        object.__setattr__(self, "image_path", _safe_relative_path(self.image_path, "image path"))
        object.__setattr__(
            self,
            "metadata_path",
            _safe_relative_path(self.metadata_path, "metadata path"),
        )


@dataclass(frozen=True, slots=True)
class CaptureDatasetManifest:
    """Versioned session inventory; raw image content remains outside Git."""

    session_id: str
    source_id: str
    frame_id: FrameId
    capture_size: ImageSize
    stored_size: ImageSize
    algorithm_size: ImageSize
    pixel_format: str
    ground_truth_class: GroundTruthClass
    frames: tuple[DatasetFrameRecord, ...]
    camera_mode: str
    capture_purpose: str = "generic"
    scaler_crop: tuple[int, int, int, int] | None = None
    hardware_manifest_ref: str | None = None
    software_versions: Mapping[str, str] = field(default_factory=dict)
    hardware_validated: bool = False

    def __post_init__(self) -> None:
        if not _SESSION_PATTERN.fullmatch(self.session_id):
            raise ValueError("session id must be a neutral 3-64 character identifier")
        if (
            not self.source_id.strip()
            or not self.pixel_format.strip()
            or not self.camera_mode.strip()
            or not self.capture_purpose.strip()
        ):
            raise ValueError("dataset source, pixel format, camera mode, and capture purpose are required")
        if self.hardware_manifest_ref is not None:
            object.__setattr__(
                self,
                "hardware_manifest_ref",
                _safe_relative_path(self.hardware_manifest_ref, "hardware manifest reference"),
            )
        if self.scaler_crop is not None:
            crop = tuple(int(value) for value in self.scaler_crop)
            if len(crop) != 4 or crop[2] <= 0 or crop[3] <= 0:
                raise ValueError("dataset scaler crop must contain x, y, positive width, and positive height")
            object.__setattr__(self, "scaler_crop", crop)
        sequence = [frame.sequence_index for frame in self.frames]
        timestamps = [frame.captured_at for frame in self.frames]
        if sequence != list(range(len(self.frames))):
            raise ValueError("dataset frame sequence must be contiguous and start at zero")
        if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
            raise ValueError("dataset frame timestamps must be strictly increasing")
        object.__setattr__(self, "software_versions", MappingProxyType(dict(self.software_versions)))

    def to_dict(self) -> dict[str, Any]:
        def size(value: ImageSize) -> dict[str, int]:
            return {"width": value.width_px, "height": value.height_px}

        return {
            "schema": "robotics-rnd-capture-dataset-v1",
            "session_id": self.session_id,
            "source_id": self.source_id,
            "frame_id": str(self.frame_id),
            "capture_size_px": size(self.capture_size),
            "stored_size_px": size(self.stored_size),
            "algorithm_size_px": size(self.algorithm_size),
            "pixel_format": self.pixel_format,
            "camera_mode": self.camera_mode,
            "capture_purpose": self.capture_purpose,
            "scaler_crop": list(self.scaler_crop) if self.scaler_crop is not None else None,
            "ground_truth_class": self.ground_truth_class.value,
            "hardware_manifest_ref": self.hardware_manifest_ref,
            "software_versions": dict(self.software_versions),
            "hardware_validated": self.hardware_validated,
            "frames": [
                {
                    "sequence_index": frame.sequence_index,
                    "captured_at": frame.captured_at.isoformat(),
                    "image_path": frame.image_path,
                    "metadata_path": frame.metadata_path,
                }
                for frame in self.frames
            ],
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> CaptureDatasetManifest:
        if document.get("schema") != "robotics-rnd-capture-dataset-v1":
            raise ValueError("unsupported capture dataset schema")

        def size(name: str) -> ImageSize:
            values = document[name]
            return ImageSize(int(values["width"]), int(values["height"]))

        return cls(
            session_id=str(document["session_id"]),
            source_id=str(document["source_id"]),
            frame_id=FrameId(str(document["frame_id"])),
            capture_size=size("capture_size_px"),
            stored_size=size("stored_size_px"),
            algorithm_size=size("algorithm_size_px"),
            pixel_format=str(document["pixel_format"]),
            camera_mode=str(document["camera_mode"]),
            capture_purpose=str(document.get("capture_purpose", "generic")),
            scaler_crop=(tuple(document["scaler_crop"]) if document.get("scaler_crop") else None),
            ground_truth_class=GroundTruthClass(str(document["ground_truth_class"])),
            hardware_manifest_ref=document.get("hardware_manifest_ref"),
            software_versions=document.get("software_versions", {}),
            hardware_validated=bool(document.get("hardware_validated", False)),
            frames=tuple(
                DatasetFrameRecord(
                    sequence_index=int(frame["sequence_index"]),
                    captured_at=datetime.fromisoformat(frame["captured_at"]),
                    image_path=str(frame["image_path"]),
                    metadata_path=str(frame["metadata_path"]),
                )
                for frame in document.get("frames", [])
            ),
        )


def save_dataset_manifest(manifest: CaptureDatasetManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_dataset_manifest(path: Path) -> CaptureDatasetManifest:
    return CaptureDatasetManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))


def validate_dataset_files(root: Path, manifest: CaptureDatasetManifest) -> None:
    """Validate file presence and frame/metadata consistency without changing data."""

    if not manifest.frames:
        raise ValueError("captured dataset contains no frames")
    for frame in manifest.frames:
        image_path = root / frame.image_path
        metadata_path = root / frame.metadata_path
        if not image_path.is_file() or not metadata_path.is_file():
            raise FileNotFoundError(f"dataset frame {frame.sequence_index} is incomplete")
        metadata = CaptureMetadata.from_dict(json.loads(metadata_path.read_text(encoding="utf-8")))
        if metadata.sequence_index != frame.sequence_index:
            raise ValueError(f"metadata sequence mismatch for frame {frame.sequence_index}")
        if metadata.capture_size != manifest.stored_size:
            raise ValueError(f"metadata image size mismatch for frame {frame.sequence_index}")
        if metadata.scaler_crop != manifest.scaler_crop:
            raise ValueError(f"metadata scaler crop mismatch for frame {frame.sequence_index}")


class DatasetImageSource:
    """Replay a validated on-disk dataset through the generic image-source API."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.manifest = load_dataset_manifest(root / "manifest.json")
        validate_dataset_files(root, self.manifest)
        self._cursor = 0

    @property
    def remaining(self) -> int:
        return len(self.manifest.frames) - self._cursor

    def reset(self) -> None:
        self._cursor = 0

    def read(self) -> ImageFrame:
        if self._cursor >= len(self.manifest.frames):
            raise StopIteration("dataset image sequence exhausted")
        record = self.manifest.frames[self._cursor]
        self._cursor += 1
        image = cv2.imread(str(self.root / record.image_path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ValueError(f"failed to decode dataset image {record.image_path}")
        metadata_document = json.loads((self.root / record.metadata_path).read_text(encoding="utf-8"))
        metadata = CaptureMetadata.from_dict(metadata_document)
        return ImageFrame(
            frame_id=self.manifest.frame_id,
            timestamp=record.captured_at,
            image=np.asarray(image, dtype=np.uint8),
            source_id=self.manifest.source_id,
            capture_metadata=metadata,
        )
