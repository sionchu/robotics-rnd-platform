"""Raspberry Pi capture, replay, pose, and benchmark CLI."""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import shutil
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter, process_time, sleep
from typing import Any

import cv2
import numpy as np

from robotics_rnd import __version__
from robotics_rnd.core import FrameId
from robotics_rnd.drivers.raspberry_pi import PiCameraConfig, PiCameraControlMode, PiCameraSource
from robotics_rnd.vision.benchmark import VisionBenchmarkResult
from robotics_rnd.vision.calibration import (
    CalibrationArtifact,
    CameraConfigurationBinding,
    CheckerboardSpec,
    calibrate_checkerboard,
    extract_checkerboard_observations,
    load_calibration_artifact,
    save_calibration_artifact,
)
from robotics_rnd.vision.camera import CameraModel, ImageFrame, ImageSize
from robotics_rnd.vision.dataset import (
    CaptureDatasetManifest,
    DatasetFrameRecord,
    DatasetImageSource,
    GroundTruthClass,
    load_dataset_manifest,
    save_dataset_manifest,
    validate_dataset_files,
)
from robotics_rnd.vision.detection import OpenCvAprilTagDetector
from robotics_rnd.vision.edge_analysis import (
    PoseFrameSample,
    analyze_pose_repeatability,
    compare_pose_runs,
)
from robotics_rnd.vision.pose import solve_apriltag_pnp


def _peak_memory_mb() -> float | None:
    """Return process peak RSS where the standard library exposes it."""

    try:
        resource = importlib.import_module("resource")
    except ModuleNotFoundError:
        return None
    peak_rss = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    divisor = 1024.0 * 1024.0 if platform.system() == "Darwin" else 1024.0
    return peak_rss / divisor


def _write_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _session_id() -> str:
    return datetime.now(UTC).strftime("pi-camera-%Y%m%dT%H%M%SZ")


def _capture_controls(arguments: argparse.Namespace) -> dict[str, Any]:
    controls: dict[str, Any] = {}
    if arguments.exposure_time_us is not None:
        controls.update({"AeEnable": False, "ExposureTime": arguments.exposure_time_us})
    if arguments.analogue_gain is not None:
        controls.update({"AeEnable": False, "AnalogueGain": arguments.analogue_gain})
    if arguments.colour_gains is not None:
        controls.update({"AwbEnable": False, "ColourGains": tuple(arguments.colour_gains)})
    if arguments.lens_position is not None:
        controls["LensPosition"] = arguments.lens_position
    if arguments.frame_duration_us is not None:
        controls["FrameDurationLimits"] = (
            arguments.frame_duration_us,
            arguments.frame_duration_us,
        )
    return controls


def capture(arguments: argparse.Namespace) -> dict[str, Any]:
    output = arguments.output
    if output.exists():
        raise ValueError("capture output directory already exists; choose a new neutral session id")
    available = shutil.disk_usage(output.parent if output.parent.exists() else Path.cwd()).free
    if available < arguments.minimum_free_mb * 1024 * 1024:
        raise OSError("insufficient free disk space for requested capture")
    output.mkdir(parents=True)
    frames_dir = output / "frames"
    metadata_dir = output / "metadata"
    frames_dir.mkdir()
    metadata_dir.mkdir()
    control_mode = (
        PiCameraControlMode.CONTROLLED if _capture_controls(arguments) else PiCameraControlMode.AUTO
    )
    config = PiCameraConfig(
        image_size=ImageSize(arguments.width, arguments.height),
        pixel_format=arguments.pixel_format,
        camera_index=arguments.camera_index,
        warmup_frames=arguments.warmup_frames,
        frame_id=FrameId(arguments.frame_id),
        source_id=arguments.source_id,
        control_mode=control_mode,
        controls=_capture_controls(arguments),
    )
    records: list[DatasetFrameRecord] = []
    scaler_crops: list[tuple[int, int, int, int] | None] = []
    with PiCameraSource(config) as source:
        for index in range(arguments.frames):
            frame = source.read()
            image_path = Path("frames") / f"{index:06d}.png"
            metadata_path = Path("metadata") / f"{index:06d}.json"
            if not cv2.imwrite(str(output / image_path), frame.image):
                raise OSError(f"failed to write frame {index}")
            assert frame.capture_metadata is not None
            scaler_crops.append(frame.capture_metadata.scaler_crop)
            _write_json(output / metadata_path, frame.capture_metadata.to_dict())
            records.append(
                DatasetFrameRecord(
                    sequence_index=index,
                    captured_at=frame.timestamp,
                    image_path=image_path.as_posix(),
                    metadata_path=metadata_path.as_posix(),
                )
            )
            if arguments.interval_s > 0.0 and index + 1 < arguments.frames:
                sleep(arguments.interval_s)
    unique_crops = set(scaler_crops)
    if len(unique_crops) != 1:
        raise ValueError("capture scaler crop changed within the dataset")
    manifest = CaptureDatasetManifest(
        session_id=arguments.session_id or _session_id(),
        source_id=config.source_id,
        frame_id=config.frame_id,
        capture_size=config.image_size,
        stored_size=config.image_size,
        algorithm_size=config.image_size,
        pixel_format=config.pixel_format,
        camera_mode=arguments.camera_mode,
        capture_purpose=arguments.capture_kind,
        scaler_crop=unique_crops.pop(),
        ground_truth_class=GroundTruthClass(arguments.ground_truth_class),
        frames=tuple(records),
        hardware_manifest_ref=arguments.hardware_manifest_ref,
        software_versions={
            "python": platform.python_version(),
            "opencv": cv2.__version__,
            "robotics_rnd": __version__,
        },
        hardware_validated=True,
    )
    save_dataset_manifest(manifest, output / "manifest.json")
    validate_dataset_files(output, manifest)
    return {
        "status": "CAPTURE_COMPLETE",
        "hardware_validated": True,
        "session_id": manifest.session_id,
        "frames": len(records),
        "output": str(output),
    }


def validate_dataset(arguments: argparse.Namespace) -> dict[str, Any]:
    manifest = load_dataset_manifest(arguments.dataset / "manifest.json")
    validate_dataset_files(arguments.dataset, manifest)
    return {
        "status": "VALID",
        "session_id": manifest.session_id,
        "frames": len(manifest.frames),
        "hardware_validated": manifest.hardware_validated,
    }


def calibrate_dataset(arguments: argparse.Namespace) -> dict[str, Any]:
    source = DatasetImageSource(arguments.dataset)
    manifest = source.manifest
    frames: list[ImageFrame] = []
    while source.remaining:
        frame = source.read()
        if frame.image_size != manifest.algorithm_size:
            resized = cv2.resize(
                frame.image,
                (manifest.algorithm_size.width_px, manifest.algorithm_size.height_px),
                interpolation=cv2.INTER_AREA,
            )
            frame = ImageFrame(
                frame_id=frame.frame_id,
                timestamp=frame.timestamp,
                image=np.asarray(resized, dtype=np.uint8),
                source_id=frame.source_id,
            )
        frames.append(frame)
    board = CheckerboardSpec(arguments.columns, arguments.rows, arguments.square_size_m)
    extraction = extract_checkerboard_observations(frames, board)
    if len(extraction.observations) < arguments.minimum_observations:
        raise ValueError(
            f"only {len(extraction.observations)} checkerboards detected; "
            f"{arguments.minimum_observations} required"
        )
    result = calibrate_checkerboard(
        extraction.observations,
        board,
        minimum_observations=arguments.minimum_observations,
    )
    result = replace(result, rejected_observations=len(extraction.rejected_source_ids))
    artifact = CalibrationArtifact(
        calibration=result,
        binding=CameraConfigurationBinding(
            sensor_model=arguments.sensor_model,
            camera_mode=manifest.camera_mode,
            capture_size=manifest.capture_size,
            calibration_size=manifest.algorithm_size,
            pixel_format=manifest.pixel_format,
            scaler_crop=manifest.scaler_crop,
        ),
        dataset_id=manifest.session_id,
        ground_truth_class=GroundTruthClass.MEASURED_PHYSICAL_REFERENCE,
        measurement_uncertainty=arguments.measurement_uncertainty,
        software_versions={
            "python": platform.python_version(),
            "opencv": cv2.__version__,
            "robotics_rnd": __version__,
        },
    )
    save_calibration_artifact(artifact, arguments.output)
    return {
        "status": "CALIBRATION_COMPLETE",
        "dataset_id": manifest.session_id,
        "accepted_observations": result.accepted_observations,
        "rejected_observations": result.rejected_observations,
        "rms_reprojection_error_px": result.metrics.rms_px,
        "output": str(arguments.output),
    }


def compare_calibrations(arguments: argparse.Namespace) -> dict[str, Any]:
    if len(arguments.artifact) < 3:
        raise ValueError("calibration repeatability comparison requires at least three artifacts")
    artifacts = [load_calibration_artifact(path) for path in arguments.artifact]
    binding = artifacts[0].binding
    if any(item.binding != binding for item in artifacts[1:]):
        raise ValueError("calibration artifacts use different camera configuration bindings")
    intrinsics = np.asarray(
        [
            (
                item.calibration.intrinsics.fx_px,
                item.calibration.intrinsics.fy_px,
                item.calibration.intrinsics.cx_px,
                item.calibration.intrinsics.cy_px,
            )
            for item in artifacts
        ],
        dtype=np.float64,
    )
    distortion = np.asarray([item.calibration.distortion.values for item in artifacts], dtype=np.float64)
    reprojection = np.asarray([item.calibration.metrics.mean_px for item in artifacts], dtype=np.float64)
    names = ("fx_px", "fy_px", "cx_px", "cy_px")
    summary = {
        "schema": "robotics-rnd-calibration-repeatability-v1",
        "runs": len(artifacts),
        "dataset_ids": [item.dataset_id for item in artifacts],
        "ground_truth_class": GroundTruthClass.MEASURED_PHYSICAL_REFERENCE.value,
        "configuration_binding": artifacts[0].to_dict()["binding"],
        "intrinsics_mean": dict(zip(names, np.mean(intrinsics, axis=0).tolist(), strict=True)),
        "intrinsics_std": dict(zip(names, np.std(intrinsics, axis=0).tolist(), strict=True)),
        "distortion_mean": np.mean(distortion, axis=0).tolist(),
        "distortion_std": np.std(distortion, axis=0).tolist(),
        "mean_reprojection_error_px": {
            "mean": float(np.mean(reprojection)),
            "std": float(np.std(reprojection)),
            "per_run": reprojection.tolist(),
        },
    }
    _write_json(arguments.output, summary)
    return {"status": "CALIBRATION_COMPARISON_COMPLETE", "output": str(arguments.output)}


def process_dataset(arguments: argparse.Namespace) -> dict[str, Any]:
    artifact = load_calibration_artifact(arguments.calibration)
    source = DatasetImageSource(arguments.dataset)
    manifest = source.manifest
    artifact.binding.assert_compatible(
        sensor_model=arguments.sensor_model,
        camera_mode=manifest.camera_mode,
        capture_size=manifest.capture_size,
        pixel_format=manifest.pixel_format,
        scaler_crop=manifest.scaler_crop,
    )
    algorithm_camera = artifact.calibration.intrinsics.scaled_to(manifest.algorithm_size)
    model = CameraModel(algorithm_camera, artifact.calibration.distortion, manifest.frame_id)
    detector = OpenCvAprilTagDetector(arguments.tag_family)
    samples: list[PoseFrameSample] = []
    processing_latencies: list[float] = []
    detector_latencies: list[float] = []
    pnp_latencies: list[float] = []
    for record in manifest.frames:
        frame = source.read()
        metadata = frame.capture_metadata
        if metadata is None:
            raise ValueError(f"dataset frame {record.sequence_index} has no capture metadata")
        analysis_frame = frame
        if frame.image_size != manifest.algorithm_size:
            resized = cv2.resize(
                frame.image,
                (manifest.algorithm_size.width_px, manifest.algorithm_size.height_px),
                interpolation=cv2.INTER_AREA,
            )
            analysis_frame = ImageFrame(
                frame_id=frame.frame_id,
                timestamp=frame.timestamp,
                image=np.asarray(resized, dtype=np.uint8),
                source_id=frame.source_id,
            )
        started = perf_counter()
        detector_started = perf_counter()
        detections = tuple(
            item for item in detector.detect(analysis_frame) if item.tag_id == arguments.tag_id
        )
        detector_latencies.append((perf_counter() - detector_started) * 1_000.0)
        if len(detections) != 1:
            samples.append(
                PoseFrameSample(
                    sequence_index=record.sequence_index,
                    monotonic_timestamp_ns=metadata.monotonic_timestamp_ns,
                    detected=False,
                )
            )
        else:
            detection = detections[0]
            pnp_started = perf_counter()
            pose = solve_apriltag_pnp(detection, model, arguments.tag_size_m)
            pnp_latencies.append((perf_counter() - pnp_started) * 1_000.0)
            transform = pose.transform
            translation = transform.translation_m.as_array()
            samples.append(
                PoseFrameSample(
                    sequence_index=record.sequence_index,
                    monotonic_timestamp_ns=metadata.monotonic_timestamp_ns,
                    detected=True,
                    translation_m=(
                        float(translation[0]),
                        float(translation[1]),
                        float(translation[2]),
                    ),
                    quaternion_xyzw=(
                        transform.rotation.x,
                        transform.rotation.y,
                        transform.rotation.z,
                        transform.rotation.w,
                    ),
                    corner_pixels=detection.corner_pixels,
                    mean_reprojection_error_px=pose.mean_reprojection_error_px,
                )
            )
        processing_latencies.append((perf_counter() - started) * 1_000.0)
    results = {
        "schema": "robotics-rnd-edge-pose-run-v1",
        "dataset_id": manifest.session_id,
        "tag_family": arguments.tag_family,
        "tag_id": arguments.tag_id,
        "tag_size_measured_m": arguments.tag_size_m,
        "transform": "T_camera_tag",
        "ground_truth_class": manifest.ground_truth_class.value,
        "hardware_validated": manifest.hardware_validated,
        "samples": [sample.to_dict() for sample in samples],
        "repeatability": analyze_pose_repeatability(tuple(samples)),
        "processing_latency_ms": {
            "mean": sum(processing_latencies) / len(processing_latencies),
            "minimum": min(processing_latencies),
            "maximum": max(processing_latencies),
            "detector_mean": sum(detector_latencies) / len(detector_latencies),
            "pnp_mean_detected_frames": (sum(pnp_latencies) / len(pnp_latencies) if pnp_latencies else None),
        },
        "software_versions": {
            "python": platform.python_version(),
            "opencv": cv2.__version__,
            "robotics_rnd": __version__,
        },
    }
    _write_json(arguments.output, results)
    return {
        "status": "PROCESSING_COMPLETE",
        "frames": len(samples),
        "detections": sum(sample.detected for sample in samples),
        "output": str(arguments.output),
    }


def benchmark(arguments: argparse.Namespace) -> dict[str, Any]:
    results_path = arguments.output.with_suffix(".pose-run.json")
    processing_values = vars(arguments).copy()
    processing_values["output"] = results_path
    processing_arguments = argparse.Namespace(**processing_values)
    wall_started = perf_counter()
    cpu_started = process_time()
    process_dataset(processing_arguments)
    wall_elapsed = perf_counter() - wall_started
    cpu_elapsed = process_time() - cpu_started
    document = json.loads(results_path.read_text(encoding="utf-8"))
    manifest = load_dataset_manifest(arguments.dataset / "manifest.json")
    latency = float(document["processing_latency_ms"]["mean"])
    detections = sum(bool(sample["detected"]) for sample in document["samples"])
    frame_count = len(document["samples"])
    peak_memory_mb = _peak_memory_mb()
    result = VisionBenchmarkResult(
        host=arguments.host_label,
        cpu=arguments.cpu_label,
        gpu=None,
        source_type="captured dataset replay",
        image_size=manifest.algorithm_size,
        algorithm=f"OpenCV AprilTag {arguments.tag_family} + PnP",
        latency_ms=latency,
        fps=1_000.0 / latency if latency > 0.0 else 0.0,
        success_rate=detections / frame_count,
        memory_mb=peak_memory_mb,
        cpu_utilization_percent=100.0 * cpu_elapsed / wall_elapsed if wall_elapsed > 0.0 else 0.0,
        stage_latencies_ms={
            "detector_mean": document["processing_latency_ms"]["detector_mean"],
            "pnp_mean_detected_frames": document["processing_latency_ms"]["pnp_mean_detected_frames"] or 0.0,
            "dataset_end_to_end_per_frame": 1_000.0 * wall_elapsed / frame_count,
        },
        accuracy_metrics={
            "mean_reprojection_error_px": document["repeatability"]["mean_reprojection_error_px"] or 0.0
        },
        software_versions=document["software_versions"],
    )
    _write_json(arguments.output, result.to_dict())
    return {"status": "BENCHMARK_COMPLETE", "output": str(arguments.output)}


def compare_runs(arguments: argparse.Namespace) -> dict[str, Any]:
    reference = json.loads(arguments.reference.read_text(encoding="utf-8"))
    candidate = json.loads(arguments.candidate.read_text(encoding="utf-8"))
    if reference.get("schema") != "robotics-rnd-edge-pose-run-v1" or candidate.get("schema") != (
        "robotics-rnd-edge-pose-run-v1"
    ):
        raise ValueError("pose-run comparison requires v1 edge pose-run files")
    if reference.get("dataset_id") != candidate.get("dataset_id"):
        raise ValueError("pose-run comparison requires the same dataset id")
    left = tuple(PoseFrameSample.from_dict(item) for item in reference["samples"])
    right = tuple(PoseFrameSample.from_dict(item) for item in candidate["samples"])
    comparison = compare_pose_runs(left, right)
    comparison["dataset_id"] = reference["dataset_id"]
    comparison["reference_software_versions"] = reference.get("software_versions", {})
    comparison["candidate_software_versions"] = candidate.get("software_versions", {})
    _write_json(arguments.output, comparison)
    return {"status": "COMPARISON_COMPLETE", "output": str(arguments.output)}


def _add_processing_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--sensor-model", required=True)
    parser.add_argument("--tag-size-m", type=float, required=True)
    parser.add_argument("--tag-family", default="tag36h11")
    parser.add_argument("--tag-id", type=int, default=7)
    parser.add_argument("--output", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--output", type=Path, required=True)
    capture_parser.add_argument("--session-id")
    capture_parser.add_argument("--frames", type=int, default=100)
    capture_parser.add_argument("--width", type=int, default=1920)
    capture_parser.add_argument("--height", type=int, default=1080)
    capture_parser.add_argument("--pixel-format", choices=("BGR888", "RGB888"), default="BGR888")
    capture_parser.add_argument("--camera-index", type=int, default=0)
    capture_parser.add_argument("--warmup-frames", type=int, default=20)
    capture_parser.add_argument("--interval-s", type=float, default=0.0)
    capture_parser.add_argument("--minimum-free-mb", type=int, default=512)
    capture_parser.add_argument("--frame-id", default="pi_camera")
    capture_parser.add_argument("--source-id", default="pi-camera")
    capture_parser.add_argument("--camera-mode", required=True)
    capture_parser.add_argument(
        "--capture-kind",
        choices=("single", "burst", "timed", "calibration", "apriltag-repeatability"),
        default="burst",
    )
    capture_parser.add_argument("--hardware-manifest-ref")
    capture_parser.add_argument(
        "--ground-truth-class",
        choices=tuple(item.value for item in GroundTruthClass),
        default=GroundTruthClass.NO_GROUND_TRUTH_REPEATABILITY_ONLY.value,
    )
    capture_parser.add_argument("--exposure-time-us", type=int)
    capture_parser.add_argument("--analogue-gain", type=float)
    capture_parser.add_argument("--colour-gains", type=float, nargs=2)
    capture_parser.add_argument("--lens-position", type=float)
    capture_parser.add_argument("--frame-duration-us", type=int)
    validate_parser = subparsers.add_parser("validate-dataset")
    validate_parser.add_argument("--dataset", type=Path, required=True)
    calibration_parser = subparsers.add_parser("calibrate-dataset")
    calibration_parser.add_argument("--dataset", type=Path, required=True)
    calibration_parser.add_argument("--sensor-model", required=True)
    calibration_parser.add_argument("--columns", type=int, default=9)
    calibration_parser.add_argument("--rows", type=int, default=6)
    calibration_parser.add_argument("--square-size-m", type=float, required=True)
    calibration_parser.add_argument("--minimum-observations", type=int, default=12)
    calibration_parser.add_argument("--measurement-uncertainty", required=True)
    calibration_parser.add_argument("--output", type=Path, required=True)
    comparison_parser = subparsers.add_parser("compare-calibrations")
    comparison_parser.add_argument("--artifact", type=Path, action="append", required=True)
    comparison_parser.add_argument("--output", type=Path, required=True)
    process_parser = subparsers.add_parser("process")
    _add_processing_arguments(process_parser)
    benchmark_parser = subparsers.add_parser("benchmark")
    _add_processing_arguments(benchmark_parser)
    benchmark_parser.add_argument("--host-label", default="edge-node-anonymized")
    benchmark_parser.add_argument("--cpu-label", default="unknown-cpu")
    compare_parser = subparsers.add_parser("compare-runs")
    compare_parser.add_argument("--reference", type=Path, required=True)
    compare_parser.add_argument("--candidate", type=Path, required=True)
    compare_parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    try:
        if arguments.command == "capture":
            if arguments.frames <= 0 or arguments.interval_s < 0.0:
                raise ValueError("frame count must be positive and interval must be non-negative")
            if arguments.capture_kind == "single" and arguments.frames != 1:
                raise ValueError("single capture requires --frames 1")
            if arguments.capture_kind == "timed" and arguments.interval_s <= 0.0:
                raise ValueError("timed capture requires a positive --interval-s")
            result = capture(arguments)
        elif arguments.command == "validate-dataset":
            result = validate_dataset(arguments)
        elif arguments.command == "calibrate-dataset":
            result = calibrate_dataset(arguments)
        elif arguments.command == "compare-calibrations":
            result = compare_calibrations(arguments)
        elif arguments.command == "process":
            result = process_dataset(arguments)
        elif arguments.command == "benchmark":
            result = benchmark(arguments)
        else:
            result = compare_runs(arguments)
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "message": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
