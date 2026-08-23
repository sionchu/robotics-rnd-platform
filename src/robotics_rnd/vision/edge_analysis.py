"""Hardware-neutral repeatability and replay-equivalence metrics."""

from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees, isfinite, sqrt
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class PoseFrameSample:
    sequence_index: int
    monotonic_timestamp_ns: int
    detected: bool
    translation_m: tuple[float, float, float] | None = None
    quaternion_xyzw: tuple[float, float, float, float] | None = None
    corner_pixels: tuple[tuple[float, float], ...] = ()
    mean_reprojection_error_px: float | None = None

    def __post_init__(self) -> None:
        if self.sequence_index < 0 or self.monotonic_timestamp_ns < 0:
            raise ValueError("pose sample sequence and timestamp must be non-negative")
        if self.detected:
            if self.translation_m is None or self.quaternion_xyzw is None or len(self.corner_pixels) != 4:
                raise ValueError("detected pose samples require translation, quaternion, and four corners")
            corner_values = tuple(value for point in self.corner_pixels for value in point)
            values = (*self.translation_m, *self.quaternion_xyzw, *corner_values)
            if not all(isfinite(value) for value in values):
                raise ValueError("pose sample values must be finite")
            norm = sqrt(sum(value * value for value in self.quaternion_xyzw))
            if norm <= np.finfo(float).eps:
                raise ValueError("pose sample quaternion norm must be non-zero")
            object.__setattr__(self, "quaternion_xyzw", tuple(value / norm for value in self.quaternion_xyzw))
        elif self.translation_m is not None or self.quaternion_xyzw is not None or self.corner_pixels:
            raise ValueError("undetected samples cannot contain pose or corners")
        if self.mean_reprojection_error_px is not None and (
            not isfinite(self.mean_reprojection_error_px) or self.mean_reprojection_error_px < 0.0
        ):
            raise ValueError("reprojection error must be finite non-negative pixels")

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_index": self.sequence_index,
            "monotonic_timestamp_ns": self.monotonic_timestamp_ns,
            "detected": self.detected,
            "translation_m": list(self.translation_m) if self.translation_m is not None else None,
            "quaternion_xyzw": list(self.quaternion_xyzw) if self.quaternion_xyzw is not None else None,
            "corner_pixels": [list(point) for point in self.corner_pixels],
            "mean_reprojection_error_px": self.mean_reprojection_error_px,
        }

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> PoseFrameSample:
        translation = document.get("translation_m")
        quaternion = document.get("quaternion_xyzw")
        return cls(
            sequence_index=int(document["sequence_index"]),
            monotonic_timestamp_ns=int(document["monotonic_timestamp_ns"]),
            detected=bool(document["detected"]),
            translation_m=tuple(translation) if translation is not None else None,
            quaternion_xyzw=tuple(quaternion) if quaternion is not None else None,
            corner_pixels=tuple(tuple(point) for point in document.get("corner_pixels", [])),
            mean_reprojection_error_px=document.get("mean_reprojection_error_px"),
        )


def _orientation_deviations_deg(quaternions: np.ndarray) -> np.ndarray:
    aligned = quaternions.copy()
    reference = aligned[0]
    for index in range(len(aligned)):
        if float(np.dot(aligned[index], reference)) < 0.0:
            aligned[index] *= -1.0
    mean = np.mean(aligned, axis=0)
    mean /= np.linalg.norm(mean)
    dots = np.clip(np.abs(aligned @ mean), 0.0, 1.0)
    return np.degrees(2.0 * np.arccos(dots))


def analyze_pose_repeatability(samples: tuple[PoseFrameSample, ...]) -> dict[str, Any]:
    if not samples:
        raise ValueError("repeatability analysis requires at least one sample")
    sequence = [sample.sequence_index for sample in samples]
    timestamps = [sample.monotonic_timestamp_ns for sample in samples]
    if sequence != sorted(sequence) or len(sequence) != len(set(sequence)):
        raise ValueError("pose samples must have unique ordered sequence indices")
    if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
        raise ValueError("pose sample timestamps must be strictly increasing")
    detected = [sample for sample in samples if sample.detected]
    result: dict[str, Any] = {
        "schema": "robotics-rnd-pose-repeatability-v1",
        "frames": len(samples),
        "detections": len(detected),
        "detection_success_rate": len(detected) / len(samples),
        "translation_mean_m": None,
        "translation_axis_std_m": None,
        "translation_rms_jitter_m": None,
        "orientation_mean_deviation_deg": None,
        "orientation_std_deviation_deg": None,
        "corner_rms_jitter_px": None,
        "mean_reprojection_error_px": None,
        "frame_interval_mean_ms": None,
        "frame_interval_std_ms": None,
    }
    intervals = np.diff(np.asarray(timestamps, dtype=np.float64)) / 1_000_000.0
    if len(intervals):
        result["frame_interval_mean_ms"] = float(np.mean(intervals))
        result["frame_interval_std_ms"] = float(np.std(intervals))
    if not detected:
        return result
    translations = np.asarray([sample.translation_m for sample in detected], dtype=np.float64)
    mean_translation = np.mean(translations, axis=0)
    result["translation_mean_m"] = mean_translation.tolist()
    result["translation_axis_std_m"] = np.std(translations, axis=0).tolist()
    result["translation_rms_jitter_m"] = float(
        np.sqrt(np.mean(np.sum(np.square(translations - mean_translation), axis=1)))
    )
    quaternions = np.asarray([sample.quaternion_xyzw for sample in detected], dtype=np.float64)
    orientation = _orientation_deviations_deg(quaternions)
    result["orientation_mean_deviation_deg"] = float(np.mean(orientation))
    result["orientation_std_deviation_deg"] = float(np.std(orientation))
    corners = np.asarray([sample.corner_pixels for sample in detected], dtype=np.float64)
    mean_corners = np.mean(corners, axis=0)
    result["corner_rms_jitter_px"] = float(
        np.sqrt(np.mean(np.sum(np.square(corners - mean_corners), axis=2)))
    )
    reprojection = [
        sample.mean_reprojection_error_px
        for sample in detected
        if sample.mean_reprojection_error_px is not None
    ]
    if reprojection:
        result["mean_reprojection_error_px"] = float(np.mean(reprojection))
    return result


def _quaternion_angle_deg(first: tuple[float, ...], second: tuple[float, ...]) -> float:
    dot = float(np.clip(abs(np.dot(first, second)), 0.0, 1.0))
    return degrees(2.0 * acos(dot))


def compare_pose_runs(
    reference: tuple[PoseFrameSample, ...],
    candidate: tuple[PoseFrameSample, ...],
) -> dict[str, Any]:
    """Compare Pi and laptop results for the same ordered dataset."""

    if len(reference) != len(candidate):
        raise ValueError("pose runs must contain the same frame count")
    disagreements = 0
    corner_deltas: list[float] = []
    translation_deltas: list[float] = []
    orientation_deltas: list[float] = []
    for left, right in zip(reference, candidate, strict=True):
        if left.sequence_index != right.sequence_index:
            raise ValueError("pose runs must have matching sequence indices")
        if left.detected != right.detected:
            disagreements += 1
            continue
        if not left.detected:
            continue
        assert left.translation_m is not None and right.translation_m is not None
        assert left.quaternion_xyzw is not None and right.quaternion_xyzw is not None
        translation_deltas.append(float(np.linalg.norm(np.subtract(left.translation_m, right.translation_m))))
        orientation_deltas.append(_quaternion_angle_deg(left.quaternion_xyzw, right.quaternion_xyzw))
        corner_deltas.append(
            float(np.max(np.linalg.norm(np.subtract(left.corner_pixels, right.corner_pixels), axis=1)))
        )
    return {
        "schema": "robotics-rnd-pose-run-comparison-v1",
        "frames": len(reference),
        "detection_disagreements": disagreements,
        "comparable_detections": len(translation_deltas),
        "max_corner_delta_px": max(corner_deltas, default=None),
        "max_translation_delta_m": max(translation_deltas, default=None),
        "max_orientation_delta_deg": max(orientation_deltas, default=None),
    }
