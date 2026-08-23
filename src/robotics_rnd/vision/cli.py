"""Small CPU-only commands for the v0.2 synthetic vision foundation."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from robotics_rnd.core import FrameId

from .calibration import CheckerboardSpec, calibrate_checkerboard, save_calibration_json
from .camera import CameraIntrinsics, CameraModel, DistortionCoefficients, ImageSize
from .camera.synthetic import generate_checkerboard_observations, render_apriltag_frame
from .detection import OpenCvAprilTagDetector
from .pose import solve_apriltag_pnp


def reference_camera(*, distorted: bool = False) -> CameraModel:
    distortion = (-0.08, 0.03, 0.0005, -0.0003, 0.0) if distorted else (0.0,) * 5
    size = ImageSize(1280, 720)
    return CameraModel(
        CameraIntrinsics(920.0, 915.0, 640.0, 360.0, size),
        DistortionCoefficients(distortion),
        FrameId("camera"),
    )


def run_calibration(seed: int, output: Path | None) -> dict[str, Any]:
    camera = reference_camera(distorted=True)
    board = CheckerboardSpec(9, 6, 0.03)
    dataset = generate_checkerboard_observations(
        camera,
        board,
        views=28,
        seed=seed,
        pixel_noise_std_px=0.15,
    )
    result = calibrate_checkerboard(dataset.observations, board)
    if output is not None:
        save_calibration_json(result, output)
    return {
        "synthetic_only": True,
        "seed": seed,
        "accepted_observations": result.accepted_observations,
        "estimated_intrinsics_px": {
            "fx": result.intrinsics.fx_px,
            "fy": result.intrinsics.fy_px,
            "cx": result.intrinsics.cx_px,
            "cy": result.intrinsics.cy_px,
        },
        "rms_reprojection_error_px": result.metrics.rms_px,
        "mean_reprojection_error_px": result.metrics.mean_px,
        "output": str(output) if output else None,
    }


def synthetic_tag_pipeline(seed: int) -> tuple[CameraModel, Any]:
    camera = reference_camera()
    frame = render_apriltag_frame(
        camera,
        tag_id=7,
        tag_size_m=0.12,
        rvec_tag_to_camera=np.array([math.pi - 0.20, 0.12, 0.08]),
        tvec_tag_to_camera_m=np.array([0.03, -0.02, 0.80]),
        image_noise_std=1.5,
        seed=seed,
    )
    detections = OpenCvAprilTagDetector("tag36h11").detect(frame)
    if len(detections) != 1:
        raise RuntimeError(f"expected one deterministic tag, detected {len(detections)}")
    return camera, detections[0]


def run_detection(seed: int) -> dict[str, Any]:
    _camera, detection = synthetic_tag_pipeline(seed)
    return {
        "synthetic_only": True,
        "seed": seed,
        "tag_family": detection.tag_family,
        "tag_id": detection.tag_id,
        "corner_order": "top-left,top-right,bottom-right,bottom-left",
        "corner_pixels": detection.corner_pixels,
        "center_pixel": detection.center_pixel,
    }


def run_pnp(seed: int) -> dict[str, Any]:
    camera, detection = synthetic_tag_pipeline(seed)
    result = solve_apriltag_pnp(detection, camera, 0.12)
    transform = result.transform
    return {
        "synthetic_only": True,
        "seed": seed,
        "transform": transform.name,
        "translation_m": transform.translation_m.as_array().tolist(),
        "quaternion_xyzw": [
            transform.rotation.x,
            transform.rotation.y,
            transform.rotation.z,
            transform.rotation.w,
        ],
        "method": result.method.value,
        "mean_reprojection_error_px": result.mean_reprojection_error_px,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260823)
    subparsers = parser.add_subparsers(dest="command", required=True)
    calibration = subparsers.add_parser("calibration", help="run synthetic checkerboard calibration")
    calibration.add_argument("--output", type=Path)
    subparsers.add_parser("apriltag", help="run synthetic AprilTag detection")
    subparsers.add_parser("pnp", help="run synthetic AprilTag detection and PnP")
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.command == "calibration":
        payload = run_calibration(arguments.seed, arguments.output)
    elif arguments.command == "apriltag":
        payload = run_detection(arguments.seed)
    else:
        payload = run_pnp(arguments.seed)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0
