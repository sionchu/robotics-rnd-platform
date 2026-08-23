"""Reproduce the five CPU-only v0.2 vision-foundation experiments."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from robotics_rnd import __version__
from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Quaternion, Transform, Vector3
from robotics_rnd.vision.benchmark import VisionBenchmarkResult
from robotics_rnd.vision.calibration import CheckerboardSpec, calibrate_checkerboard, save_calibration_json
from robotics_rnd.vision.camera import CameraIntrinsics, CameraModel, DistortionCoefficients, ImageSize
from robotics_rnd.vision.camera.synthetic import (
    april_tag_object_corners_m,
    generate_checkerboard_observations,
    render_apriltag_frame,
)
from robotics_rnd.vision.detection import AprilTagObservation, OpenCvAprilTagDetector
from robotics_rnd.vision.pose import compare_pose, solve_apriltag_pnp, transform_from_rvec_tvec
from robotics_rnd.vision.pose.reprojection import project_points

ROOT = Path(__file__).resolve().parents[2]
SEED = 20260823
CAMERA_FRAME = FrameId("camera")
TAG_FRAME = FrameId("tag")
WRITE_RESULTS = True


def write_json(path: Path, document: Any) -> None:
    if not WRITE_RESULTS:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reference_camera(*, distorted: bool = False) -> CameraModel:
    size = ImageSize(1280, 720)
    distortion = (-0.08, 0.03, 0.0005, -0.0003, 0.0) if distorted else (0.0,) * 5
    return CameraModel(
        CameraIntrinsics(920.0, 915.0, 640.0, 360.0, size),
        DistortionCoefficients(distortion),
        CAMERA_FRAME,
    )


def exact_observation(
    camera: CameraModel,
    rvec: NDArray[np.float64],
    tvec_m: NDArray[np.float64],
    *,
    noise_std_px: float = 0.0,
    rng: np.random.Generator | None = None,
) -> AprilTagObservation:
    corners = project_points(april_tag_object_corners_m(0.12), rvec, tvec_m, camera)
    if noise_std_px:
        if rng is None:
            raise ValueError("a random generator is required when adding pixel noise")
        corners = corners + rng.normal(0.0, noise_std_px, corners.shape)
    ordered = tuple((float(x), float(y)) for x, y in corners)
    return AprilTagObservation(
        "tag36h11",
        7,
        ordered,
        datetime(2026, 8, 23, tzinfo=UTC),
        CAMERA_FRAME,
        camera.image_size,
    )


def run_calibration() -> dict[str, Any]:
    output = ROOT / "experiments/vision/001_camera_calibration/results"
    camera = reference_camera(distorted=True)
    board = CheckerboardSpec(9, 6, 0.03)
    dataset = generate_checkerboard_observations(
        camera,
        board,
        views=28,
        seed=SEED,
        pixel_noise_std_px=0.15,
    )
    result = calibrate_checkerboard(dataset.observations, board)
    result = replace(result, created_at=datetime(2026, 8, 23, tzinfo=UTC))
    if WRITE_RESULTS:
        save_calibration_json(result, output / "calibration.json")
    estimate = result.intrinsics
    truth = camera.intrinsics
    distortion_error = float(
        np.linalg.norm(np.asarray(result.distortion.values) - np.asarray(camera.distortion.values))
    )
    metrics = {
        "experiment": "001_camera_calibration",
        "synthetic_only": True,
        "seed": SEED,
        "opencv_version": cv2.__version__,
        "views": len(dataset.observations),
        "pixel_noise_std_px": dataset.pixel_noise_std_px,
        "generator_rejected_proposals": dataset.rejected_proposals,
        "ground_truth_intrinsics_px": {
            "fx": truth.fx_px,
            "fy": truth.fy_px,
            "cx": truth.cx_px,
            "cy": truth.cy_px,
        },
        "estimated_intrinsics_px": {
            "fx": estimate.fx_px,
            "fy": estimate.fy_px,
            "cx": estimate.cx_px,
            "cy": estimate.cy_px,
        },
        "relative_fx_error": abs(estimate.fx_px - truth.fx_px) / truth.fx_px,
        "relative_fy_error": abs(estimate.fy_px - truth.fy_px) / truth.fy_px,
        "principal_point_error_px": float(
            np.linalg.norm([estimate.cx_px - truth.cx_px, estimate.cy_px - truth.cy_px])
        ),
        "distortion_l2_error": distortion_error,
        "rms_reprojection_error_px": result.metrics.rms_px,
        "mean_reprojection_error_px": result.metrics.mean_px,
        "max_reprojection_error_px": result.metrics.max_px,
        "per_view_rms_px": result.metrics.per_view_rms_px,
        "accepted_observations": result.accepted_observations,
        "rejected_observations": result.rejected_observations,
        "acceptance": {
            "relative_focal_error_below_0_5_percent": (
                abs(estimate.fx_px - truth.fx_px) / truth.fx_px < 0.005
                and abs(estimate.fy_px - truth.fy_px) / truth.fy_px < 0.005
            ),
            "principal_point_error_below_2_px": float(
                np.linalg.norm([estimate.cx_px - truth.cx_px, estimate.cy_px - truth.cy_px])
            )
            < 2.0,
            "mean_reprojection_below_0_3_px": result.metrics.mean_px < 0.3,
            "distortion_l2_error_below_0_02": distortion_error < 0.02,
        },
    }
    write_json(output / "metrics.json", metrics)
    if not all(metrics["acceptance"].values()):
        raise RuntimeError("camera-calibration acceptance gate failed")
    return metrics


def run_apriltag() -> dict[str, Any]:
    root = ROOT / "experiments/vision/002_apriltag_detection"
    output = root / "results"
    fixtures = root / "tests/fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    camera = reference_camera()
    detector = OpenCvAprilTagDetector("tag36h11")
    scenarios: tuple[tuple[str, NDArray[np.float64], NDArray[np.float64], float, float], ...] = (
        ("baseline", np.array([math.pi - 0.20, 0.12, 0.08]), np.array([0.0, 0.0, 0.75]), 0.0, 0.0),
        ("small", np.array([math.pi - 0.15, 0.08, -0.05]), np.array([0.0, 0.0, 1.50]), 0.0, 0.0),
        ("translated", np.array([math.pi - 0.20, 0.12, 0.08]), np.array([0.20, -0.10, 0.90]), 0.0, 0.0),
        ("rotated", np.array([math.pi - 0.35, 0.18, 0.45]), np.array([0.0, 0.0, 0.85]), 0.0, 0.0),
        ("perspective", np.array([math.pi - 0.70, 0.32, 0.08]), np.array([0.0, 0.0, 0.80]), 0.0, 0.0),
        ("blur", np.array([math.pi - 0.20, 0.12, 0.08]), np.array([0.0, 0.0, 0.80]), 2.0, 0.0),
        ("noise", np.array([math.pi - 0.20, 0.12, 0.08]), np.array([0.0, 0.0, 0.80]), 0.0, 10.0),
        ("blur_noise", np.array([math.pi - 0.40, 0.18, 0.15]), np.array([0.0, 0.0, 1.10]), 2.0, 8.0),
    )
    records: list[dict[str, Any]] = []
    latencies: list[float] = []
    for index, (name, rvec, tvec, blur, noise) in enumerate(scenarios):
        frame = render_apriltag_frame(
            camera,
            tag_id=7,
            tag_size_m=0.12,
            rvec_tag_to_camera=rvec,
            tvec_tag_to_camera_m=tvec,
            blur_sigma_px=blur,
            image_noise_std=noise,
            seed=SEED + index,
            source_id=f"synthetic-{name}",
            timestamp_offset_ms=index,
        )
        started = perf_counter()
        detections = detector.detect(frame)
        latencies.append((perf_counter() - started) * 1_000.0)
        expected = project_points(april_tag_object_corners_m(0.12), rvec, tvec, camera)
        correct = len(detections) == 1 and detections[0].tag_id == 7
        corner_rmse = None
        if correct:
            observed = np.asarray(detections[0].corner_pixels)
            corner_rmse = float(np.sqrt(np.mean(np.square(observed - expected))))
        if (
            WRITE_RESULTS
            and name not in {"noise", "blur_noise"}
            and not cv2.imwrite(str(fixtures / f"{name}.png"), frame.image)
        ):
            raise RuntimeError(f"failed to write deterministic fixture {name}")
        records.append(
            {
                "scenario": name,
                "detected": bool(detections),
                "correct_id": correct,
                "detections": len(detections),
                "corner_rmse_px": corner_rmse,
                "blur_sigma_px": blur,
                "image_noise_std": noise,
            }
        )
    success_rate = sum(record["correct_id"] for record in records) / len(records)
    mean_latency = float(np.mean(latencies))
    benchmark = VisionBenchmarkResult(
        host="ubuntu-workstation-anonymized",
        cpu="AMD Ryzen AI 7 350",
        gpu=None,
        source_type="synthetic grayscale PNG",
        image_size=camera.image_size,
        algorithm="OpenCV ArucoDetector AprilTag 36h11",
        latency_ms=mean_latency,
        fps=1_000.0 / mean_latency,
        success_rate=success_rate,
        accuracy_metrics={
            "mean_corner_rmse_px": float(
                np.mean(
                    [record["corner_rmse_px"] for record in records if record["corner_rmse_px"] is not None]
                )
            )
        },
        software_versions={"opencv": cv2.__version__, "robotics_rnd": __version__},
    )
    metrics = {
        "experiment": "002_apriltag_detection",
        "synthetic_only": True,
        "seed": SEED,
        "dependency": "opencv-python-headless",
        "dependency_version": cv2.__version__,
        "family": "tag36h11",
        "corner_order": "top-left,top-right,bottom-right,bottom-left",
        "scenarios": records,
        "detection_success_rate": success_rate,
        "benchmark": benchmark.to_dict(),
        "acceptance": {"all_expected_tags_detected": success_rate == 1.0},
    }
    write_json(output / "metrics.json", metrics)
    write_json(output / "benchmark.json", benchmark.to_dict())
    if success_rate != 1.0:
        raise RuntimeError("AprilTag detection acceptance gate failed")
    return metrics


def run_pnp() -> dict[str, Any]:
    output = ROOT / "experiments/vision/003_apriltag_pnp_pose/results"
    camera = reference_camera()
    cases: tuple[tuple[str, NDArray[np.float64], NDArray[np.float64]], ...] = (
        ("front_facing", np.array([math.pi, 0.0, 0.0]), np.array([0.0, 0.0, 0.8])),
        ("translated", np.array([math.pi - 0.20, 0.12, 0.08]), np.array([0.12, -0.06, 0.9])),
        ("rotated", np.array([math.pi - 0.55, -0.22, 0.18]), np.array([0.02, 0.03, 0.75])),
        ("far", np.array([math.pi - 0.30, 0.15, -0.10]), np.array([-0.10, 0.04, 1.6])),
    )
    records: list[dict[str, Any]] = []
    for name, rvec, tvec in cases:
        observation = exact_observation(camera, rvec, tvec)
        result = solve_apriltag_pnp(observation, camera, 0.12, tag_frame=TAG_FRAME)
        expected = transform_from_rvec_tvec(
            rvec,
            tvec,
            target_frame=CAMERA_FRAME,
            source_frame=TAG_FRAME,
        )
        errors = compare_pose(
            result.transform,
            expected,
            mean_reprojection_error_px=result.mean_reprojection_error_px,
        )
        records.append(
            {
                "case": name,
                "transform": result.transform.name,
                "selected_method": result.method.value,
                "translation_error_m": errors.translation_error_m,
                "relative_translation_error_percent": errors.relative_translation_error_percent,
                "orientation_error_deg": errors.orientation_error_deg,
                "mean_reprojection_error_px": errors.mean_reprojection_error_px,
            }
        )

    raster_rvec = np.array([math.pi - 0.20, 0.12, 0.08])
    raster_tvec = np.array([0.03, -0.02, 0.8])
    frame = render_apriltag_frame(
        camera,
        tag_id=7,
        tag_size_m=0.12,
        rvec_tag_to_camera=raster_rvec,
        tvec_tag_to_camera_m=raster_tvec,
        image_noise_std=1.5,
        seed=SEED,
    )
    detection = OpenCvAprilTagDetector().detect(frame)[0]
    raster_result = solve_apriltag_pnp(detection, camera, 0.12, tag_frame=TAG_FRAME)
    raster_truth = transform_from_rvec_tvec(
        raster_rvec,
        raster_tvec,
        target_frame=CAMERA_FRAME,
        source_frame=TAG_FRAME,
    )
    raster_errors = compare_pose(
        raster_result.transform,
        raster_truth,
        mean_reprojection_error_px=raster_result.mean_reprojection_error_px,
    )
    exact_pass = all(
        record["translation_error_m"] < 1.0e-8
        and record["orientation_error_deg"] < 1.0e-5
        and record["mean_reprojection_error_px"] < 1.0e-7
        for record in records
    )
    metrics = {
        "experiment": "003_apriltag_pnp_pose",
        "synthetic_only": True,
        "tag_size_m": 0.12,
        "requested_default": "IPPE_SQUARE",
        "transform_convention": "T_camera_tag maps tag coordinates into camera",
        "exact_corner_cases": records,
        "raster_detection_case": {
            "translation_error_m": raster_errors.translation_error_m,
            "relative_translation_error_percent": raster_errors.relative_translation_error_percent,
            "orientation_error_deg": raster_errors.orientation_error_deg,
            "mean_reprojection_error_px": raster_errors.mean_reprojection_error_px,
        },
        "acceptance": {
            "exact_cases_near_numerical_precision": exact_pass,
            "transform_direction_is_T_camera_tag": all(
                record["transform"] == "T_camera_tag" for record in records
            ),
        },
    }
    write_json(output / "metrics.json", metrics)
    if not all(metrics["acceptance"].values()):
        raise RuntimeError("PnP acceptance gate failed")
    return metrics


def axis_angle(axis: NDArray[np.float64], angle: float) -> Quaternion:
    normalized = axis / np.linalg.norm(axis)
    sine = math.sin(angle / 2.0)
    return Quaternion(
        float(normalized[0] * sine),
        float(normalized[1] * sine),
        float(normalized[2] * sine),
        math.cos(angle / 2.0),
    )


def run_transform_chain() -> dict[str, Any]:
    output = ROOT / "experiments/vision/004_transform_chain/results"
    rng = np.random.default_rng(SEED)
    base, camera, tag = FrameId("base"), CAMERA_FRAME, TAG_FRAME
    composition_errors: list[float] = []
    inverse_errors: list[float] = []
    cases = 100
    for _case in range(cases):
        t_base_camera = Transform(
            base,
            camera,
            Vector3.from_iterable(rng.uniform(-1.0, 1.0, 3)),
            axis_angle(rng.normal(size=3), float(rng.uniform(-math.pi, math.pi))),
        )
        t_camera_tag = Transform(
            camera,
            tag,
            Vector3.from_iterable(rng.uniform(-1.0, 1.0, 3)),
            axis_angle(rng.normal(size=3), float(rng.uniform(-math.pi, math.pi))),
        )
        t_base_tag = t_base_camera @ t_camera_tag
        expected = t_base_camera.as_matrix() @ t_camera_tag.as_matrix()
        composition_errors.append(float(np.max(np.abs(t_base_tag.as_matrix() - expected))))
        recovered = t_base_camera.inverse() @ t_base_tag
        inverse_errors.append(float(np.max(np.abs(recovered.as_matrix() - t_camera_tag.as_matrix()))))
    reverse_rejected = False
    try:
        t_camera_tag @ t_base_camera
    except ValueError:
        reverse_rejected = True
    metrics = {
        "experiment": "004_transform_chain",
        "synthetic_only": True,
        "seed": SEED,
        "cases": cases,
        "composition": "T_base_camera @ T_camera_tag = T_base_tag",
        "max_composition_matrix_error": max(composition_errors),
        "max_inverse_recovery_matrix_error": max(inverse_errors),
        "reversed_composition_rejected": reverse_rejected,
        "acceptance": {
            "composition_below_1e_12": max(composition_errors) < 1.0e-12,
            "inverse_recovery_below_1e_12": max(inverse_errors) < 1.0e-12,
            "reversed_composition_rejected": reverse_rejected,
        },
    }
    write_json(output / "metrics.json", metrics)
    if not all(metrics["acceptance"].values()):
        raise RuntimeError("transform-chain acceptance gate failed")
    return metrics


def tilted_tag_rvec(tilt_deg: float, yaw_deg: float = 0.0) -> NDArray[np.float64]:
    """Create tag-to-camera rotation from the front-facing tag convention."""

    front = np.diag([1.0, -1.0, -1.0])
    tilt, _ = cv2.Rodrigues(np.array([0.0, math.radians(tilt_deg), 0.0]))
    yaw, _ = cv2.Rodrigues(np.array([0.0, 0.0, math.radians(yaw_deg)]))
    rvec, _ = cv2.Rodrigues(yaw @ tilt @ front)
    return np.asarray(rvec, dtype=np.float64).reshape(3)


def perturbed_camera(truth: CameraModel, fraction: float) -> CameraModel:
    intrinsics = truth.intrinsics
    return CameraModel(
        CameraIntrinsics(
            intrinsics.fx_px * (1.0 + fraction),
            intrinsics.fy_px * (1.0 - fraction),
            intrinsics.cx_px + 500.0 * fraction,
            intrinsics.cy_px - 250.0 * fraction,
            intrinsics.image_size,
        ),
        truth.distortion,
        truth.frame_id,
    )


def aggregate_sensitivity_case(
    *,
    factor: str,
    level: float,
    distance_m: float,
    tilt_deg: float,
    pixel_noise_std_px: float,
    intrinsic_perturbation_fraction: float,
    trials: int,
    rng: np.random.Generator,
) -> dict[str, Any]:
    truth_camera = reference_camera()
    solve_camera = perturbed_camera(truth_camera, intrinsic_perturbation_fraction)
    rvec = tilted_tag_rvec(tilt_deg, yaw_deg=8.0)
    tvec = np.array([0.02, -0.01, distance_m])
    expected = transform_from_rvec_tvec(
        rvec,
        tvec,
        target_frame=CAMERA_FRAME,
        source_frame=TAG_FRAME,
    )
    exact_corners = project_points(april_tag_object_corners_m(0.12), rvec, tvec, truth_camera)
    edge_lengths = np.linalg.norm(np.roll(exact_corners, -1, axis=0) - exact_corners, axis=1)
    translation_errors: list[float] = []
    orientation_errors: list[float] = []
    reprojection_errors: list[float] = []
    success = 0
    for _trial in range(trials):
        try:
            observation = exact_observation(
                truth_camera,
                rvec,
                tvec,
                noise_std_px=pixel_noise_std_px,
                rng=rng,
            )
            result = solve_apriltag_pnp(observation, solve_camera, 0.12, tag_frame=TAG_FRAME)
            errors = compare_pose(
                result.transform,
                expected,
                mean_reprojection_error_px=result.mean_reprojection_error_px,
            )
        except (RuntimeError, ValueError):
            continue
        success += 1
        translation_errors.append(errors.translation_error_m)
        orientation_errors.append(errors.orientation_error_deg)
        reprojection_errors.append(errors.mean_reprojection_error_px)
    if not translation_errors:
        return {
            "factor": factor,
            "level": level,
            "distance_m": distance_m,
            "tilt_deg": tilt_deg,
            "tag_edge_px": float(np.mean(edge_lengths)),
            "pixel_noise_std_px": pixel_noise_std_px,
            "intrinsic_perturbation_fraction": intrinsic_perturbation_fraction,
            "trials": trials,
            "success_rate": 0.0,
            "mean_translation_error_mm": None,
            "p95_translation_error_mm": None,
            "mean_orientation_error_deg": None,
            "p95_orientation_error_deg": None,
            "mean_reprojection_error_px": None,
        }
    return {
        "factor": factor,
        "level": level,
        "distance_m": distance_m,
        "tilt_deg": tilt_deg,
        "tag_edge_px": float(np.mean(edge_lengths)),
        "pixel_noise_std_px": pixel_noise_std_px,
        "intrinsic_perturbation_fraction": intrinsic_perturbation_fraction,
        "trials": trials,
        "success_rate": success / trials,
        "mean_translation_error_mm": 1_000.0 * float(np.mean(translation_errors)),
        "p95_translation_error_mm": 1_000.0 * float(np.percentile(translation_errors, 95)),
        "mean_orientation_error_deg": float(np.mean(orientation_errors)),
        "p95_orientation_error_deg": float(np.percentile(orientation_errors, 95)),
        "mean_reprojection_error_px": float(np.mean(reprojection_errors)),
    }


def blur_detection_rows(rng: np.random.Generator) -> list[dict[str, Any]]:
    camera = reference_camera()
    detector = OpenCvAprilTagDetector()
    rows: list[dict[str, Any]] = []
    for blur in (0.0, 1.5, 3.0, 5.0):
        translation_errors: list[float] = []
        orientation_errors: list[float] = []
        reprojection_errors: list[float] = []
        successes = 0
        trials = 12
        edge_sizes: list[float] = []
        for trial in range(trials):
            rvec = tilted_tag_rvec(20.0 + trial % 4, yaw_deg=-8.0 + trial)
            tvec = np.array([0.0, 0.0, 1.4])
            exact_corners = project_points(april_tag_object_corners_m(0.12), rvec, tvec, camera)
            edge_sizes.append(
                float(np.mean(np.linalg.norm(np.roll(exact_corners, -1, axis=0) - exact_corners, axis=1)))
            )
            frame = render_apriltag_frame(
                camera,
                tag_id=7,
                tag_size_m=0.12,
                rvec_tag_to_camera=rvec,
                tvec_tag_to_camera_m=tvec,
                blur_sigma_px=blur,
                image_noise_std=8.0,
                seed=int(rng.integers(0, 2**31 - 1)),
            )
            detections = detector.detect(frame)
            if len(detections) != 1:
                continue
            try:
                result = solve_apriltag_pnp(detections[0], camera, 0.12, tag_frame=TAG_FRAME)
                expected = transform_from_rvec_tvec(
                    rvec,
                    tvec,
                    target_frame=CAMERA_FRAME,
                    source_frame=TAG_FRAME,
                )
                errors = compare_pose(
                    result.transform,
                    expected,
                    mean_reprojection_error_px=result.mean_reprojection_error_px,
                )
            except (RuntimeError, ValueError):
                continue
            successes += 1
            translation_errors.append(errors.translation_error_m)
            orientation_errors.append(errors.orientation_error_deg)
            reprojection_errors.append(errors.mean_reprojection_error_px)
        rows.append(
            {
                "factor": "blur_sigma_px",
                "level": blur,
                "distance_m": 1.4,
                "tilt_deg": 20.0,
                "tag_edge_px": float(np.mean(edge_sizes)),
                "pixel_noise_std_px": 8.0,
                "intrinsic_perturbation_fraction": 0.0,
                "trials": trials,
                "success_rate": successes / trials,
                "mean_translation_error_mm": (
                    1_000.0 * float(np.mean(translation_errors)) if translation_errors else None
                ),
                "p95_translation_error_mm": (
                    1_000.0 * float(np.percentile(translation_errors, 95)) if translation_errors else None
                ),
                "mean_orientation_error_deg": (
                    float(np.mean(orientation_errors)) if orientation_errors else None
                ),
                "p95_orientation_error_deg": (
                    float(np.percentile(orientation_errors, 95)) if orientation_errors else None
                ),
                "mean_reprojection_error_px": (
                    float(np.mean(reprojection_errors)) if reprojection_errors else None
                ),
            }
        )
    return rows


def run_sensitivity() -> dict[str, Any]:
    output = ROOT / "experiments/vision/005_pose_sensitivity/results"
    rng = np.random.default_rng(SEED)
    rows: list[dict[str, Any]] = []
    trials = 30
    for distance in (0.5, 0.8, 1.2, 1.6):
        rows.append(
            aggregate_sensitivity_case(
                factor="distance_m",
                level=distance,
                distance_m=distance,
                tilt_deg=20.0,
                pixel_noise_std_px=0.5,
                intrinsic_perturbation_fraction=0.0,
                trials=trials,
                rng=rng,
            )
        )
    for tilt in (5.0, 20.0, 40.0, 60.0):
        rows.append(
            aggregate_sensitivity_case(
                factor="tilt_deg",
                level=tilt,
                distance_m=0.8,
                tilt_deg=tilt,
                pixel_noise_std_px=0.5,
                intrinsic_perturbation_fraction=0.0,
                trials=trials,
                rng=rng,
            )
        )
    for noise in (0.0, 0.25, 0.5, 1.0, 2.0):
        rows.append(
            aggregate_sensitivity_case(
                factor="pixel_noise_std_px",
                level=noise,
                distance_m=0.8,
                tilt_deg=20.0,
                pixel_noise_std_px=noise,
                intrinsic_perturbation_fraction=0.0,
                trials=trials,
                rng=rng,
            )
        )
    for perturbation in (0.0, 0.005, 0.01, 0.02):
        rows.append(
            aggregate_sensitivity_case(
                factor="intrinsic_perturbation_fraction",
                level=perturbation,
                distance_m=0.8,
                tilt_deg=20.0,
                pixel_noise_std_px=0.0,
                intrinsic_perturbation_fraction=perturbation,
                trials=trials,
                rng=rng,
            )
        )
    rows.extend(blur_detection_rows(rng))

    if WRITE_RESULTS:
        output.mkdir(parents=True, exist_ok=True)
        fieldnames = tuple(rows[0])
        with (output / "sensitivity.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    factor_changes: list[dict[str, Any]] = []
    for factor in sorted({str(row["factor"]) for row in rows}):
        factor_rows = [row for row in rows if row["factor"] == factor]
        first = factor_rows[0]["mean_translation_error_mm"]
        last = factor_rows[-1]["mean_translation_error_mm"]
        factor_changes.append(
            {
                "factor": factor,
                "first_level": factor_rows[0]["level"],
                "last_level": factor_rows[-1]["level"],
                "translation_error_change_mm": (
                    float(last) - float(first) if first is not None and last is not None else None
                ),
                "success_rate_change": factor_rows[-1]["success_rate"] - factor_rows[0]["success_rate"],
            }
        )
    zero_noise = next(row for row in rows if row["factor"] == "pixel_noise_std_px" and row["level"] == 0.0)
    metrics = {
        "experiment": "005_pose_sensitivity",
        "synthetic_only": True,
        "seed": SEED,
        "design": "one-factor-at-a-time with 30 PnP trials; 12 image-detection trials per blur level",
        "factors": [
            "distance_m",
            "tilt_deg",
            "pixel_noise_std_px",
            "intrinsic_perturbation_fraction",
            "blur_sigma_px",
        ],
        "rows": rows,
        "factor_endpoint_changes": factor_changes,
        "acceptance": {
            "zero_noise_translation_below_1e_5_mm": zero_noise["mean_translation_error_mm"] < 1.0e-5,
            "zero_noise_orientation_below_1e_5_deg": zero_noise["mean_orientation_error_deg"] < 1.0e-5,
            "all_rows_record_success_rate": all(0.0 <= row["success_rate"] <= 1.0 for row in rows),
        },
    }
    write_json(output / "metrics.json", metrics)
    if not all(metrics["acceptance"].values()):
        raise RuntimeError("pose-sensitivity acceptance gate failed")
    return metrics


RUNNERS: dict[str, Callable[[], dict[str, Any]]] = {
    "calibration": run_calibration,
    "apriltag": run_apriltag,
    "pnp": run_pnp,
    "transform": run_transform_chain,
    "sensitivity": run_sensitivity,
}


def main() -> int:
    global WRITE_RESULTS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", choices=(*RUNNERS, "all"))
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="run all calculations and gates without rewriting tracked result artifacts",
    )
    arguments = parser.parse_args()
    WRITE_RESULTS = not arguments.verify_only
    selected = (
        RUNNERS if arguments.experiment == "all" else {arguments.experiment: RUNNERS[arguments.experiment]}
    )
    summaries: dict[str, Any] = {}
    for name, runner in selected.items():
        result = runner()
        summaries[name] = {"acceptance": result["acceptance"]}
    print(json.dumps(summaries, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
