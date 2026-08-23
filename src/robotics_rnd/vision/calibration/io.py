"""Portable JSON persistence for camera calibration results."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from robotics_rnd.vision.camera import CameraIntrinsics, DistortionCoefficients, ImageSize

from .metrics import ReprojectionMetrics
from .models import CameraCalibrationResult


def calibration_to_dict(result: CameraCalibrationResult) -> dict[str, Any]:
    intrinsics = result.intrinsics
    return {
        "schema": "robotics-rnd-camera-calibration-v1",
        "image_size_px": {
            "width": intrinsics.image_size.width_px,
            "height": intrinsics.image_size.height_px,
        },
        "intrinsics_px": {
            "fx": intrinsics.fx_px,
            "fy": intrinsics.fy_px,
            "cx": intrinsics.cx_px,
            "cy": intrinsics.cy_px,
        },
        "distortion": {
            "model": result.distortion.model,
            "coefficients": list(result.distortion.values),
        },
        "target": result.target,
        "method": result.method,
        "accepted_observations": result.accepted_observations,
        "rejected_observations": result.rejected_observations,
        "reprojection_px": {
            "rms": result.metrics.rms_px,
            "mean": result.metrics.mean_px,
            "max": result.metrics.max_px,
            "per_view_rms": list(result.metrics.per_view_rms_px),
        },
        "created_at": result.created_at.isoformat(),
        "software_version": result.software_version,
        "units": {"image": "pixels", "target_lengths": "metres"},
    }


def save_calibration_json(result: CameraCalibrationResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(calibration_to_dict(result), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def load_calibration_json(path: Path) -> CameraCalibrationResult:
    return calibration_from_dict(json.loads(path.read_text(encoding="utf-8")))


def calibration_from_dict(document: dict[str, Any]) -> CameraCalibrationResult:
    if document.get("schema") != "robotics-rnd-camera-calibration-v1":
        raise ValueError("unsupported calibration schema")
    size = document["image_size_px"]
    values = document["intrinsics_px"]
    reprojection = document["reprojection_px"]
    distortion = document["distortion"]
    return CameraCalibrationResult(
        intrinsics=CameraIntrinsics(
            fx_px=values["fx"],
            fy_px=values["fy"],
            cx_px=values["cx"],
            cy_px=values["cy"],
            image_size=ImageSize(width_px=size["width"], height_px=size["height"]),
        ),
        distortion=DistortionCoefficients(tuple(distortion["coefficients"]), distortion["model"]),
        metrics=ReprojectionMetrics(
            rms_px=reprojection["rms"],
            mean_px=reprojection["mean"],
            max_px=reprojection["max"],
            per_view_rms_px=tuple(reprojection["per_view_rms"]),
        ),
        method=document["method"],
        target=document["target"],
        accepted_observations=document["accepted_observations"],
        rejected_observations=document["rejected_observations"],
        created_at=datetime.fromisoformat(document["created_at"]),
        software_version=document["software_version"],
    )
