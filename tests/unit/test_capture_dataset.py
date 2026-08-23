from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
import pytest

from robotics_rnd.core import FrameId
from robotics_rnd.vision.camera import CaptureMetadata, ImageSize
from robotics_rnd.vision.dataset import (
    CaptureDatasetManifest,
    DatasetFrameRecord,
    DatasetImageSource,
    GroundTruthClass,
    load_dataset_manifest,
    save_dataset_manifest,
    validate_dataset_files,
)


def write_dataset(root: Path) -> CaptureDatasetManifest:
    size = ImageSize(32, 24)
    records: list[DatasetFrameRecord] = []
    for index in range(2):
        image_path = Path("frames") / f"{index:06d}.png"
        metadata_path = Path("metadata") / f"{index:06d}.json"
        (root / image_path).parent.mkdir(parents=True, exist_ok=True)
        (root / metadata_path).parent.mkdir(parents=True, exist_ok=True)
        assert cv2.imwrite(str(root / image_path), np.full((*size.shape, 3), index, dtype=np.uint8))
        metadata = CaptureMetadata(index, 1_000_000 + index, size, "BGR888")
        (root / metadata_path).write_text(json.dumps(metadata.to_dict()), encoding="utf-8")
        records.append(
            DatasetFrameRecord(
                index,
                datetime(2026, 8, 23, tzinfo=UTC) + timedelta(milliseconds=index),
                image_path.as_posix(),
                metadata_path.as_posix(),
            )
        )
    manifest = CaptureDatasetManifest(
        session_id="pi-camera-test",
        source_id="pi-camera",
        frame_id=FrameId("pi_camera"),
        capture_size=size,
        stored_size=size,
        algorithm_size=size,
        pixel_format="BGR888",
        ground_truth_class=GroundTruthClass.NO_GROUND_TRUTH_REPEATABILITY_ONLY,
        frames=tuple(records),
        camera_mode="test-mode",
        hardware_validated=False,
    )
    save_dataset_manifest(manifest, root / "manifest.json")
    return manifest


def test_dataset_manifest_validation_and_replay(tmp_path: Path) -> None:
    manifest = write_dataset(tmp_path)
    assert load_dataset_manifest(tmp_path / "manifest.json") == manifest
    validate_dataset_files(tmp_path, manifest)
    source = DatasetImageSource(tmp_path)
    assert source.read().capture_metadata.sequence_index == 0
    assert source.read().capture_metadata.sequence_index == 1
    with pytest.raises(StopIteration):
        source.read()
    source.reset()
    assert source.remaining == 2


def test_dataset_rejects_missing_files_unsafe_paths_and_bad_order(tmp_path: Path) -> None:
    manifest = write_dataset(tmp_path)
    (tmp_path / manifest.frames[1].image_path).unlink()
    with pytest.raises(FileNotFoundError, match="incomplete"):
        validate_dataset_files(tmp_path, manifest)
    with pytest.raises(ValueError, match="safe relative"):
        DatasetFrameRecord(0, datetime.now(UTC), "../frame.png", "metadata/0.json")
    with pytest.raises(ValueError, match="contiguous"):
        CaptureDatasetManifest(
            session_id="bad-sequence",
            source_id="camera",
            frame_id=FrameId("camera"),
            capture_size=ImageSize(1, 1),
            stored_size=ImageSize(1, 1),
            algorithm_size=ImageSize(1, 1),
            pixel_format="BGR888",
            ground_truth_class=GroundTruthClass.NO_GROUND_TRUTH_REPEATABILITY_ONLY,
            frames=(DatasetFrameRecord(2, datetime.now(UTC), "frames/2.png", "metadata/2.json"),),
            camera_mode="mode",
        )
