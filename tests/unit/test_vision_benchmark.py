import pytest

from robotics_rnd.vision.benchmark import VisionBenchmarkResult
from robotics_rnd.vision.camera import ImageSize


def test_benchmark_schema_is_portable_and_validated() -> None:
    result = VisionBenchmarkResult(
        host="generic-workstation",
        cpu="generic-cpu",
        gpu=None,
        source_type="synthetic",
        image_size=ImageSize(640, 480),
        algorithm="OpenCV AprilTag 36h11",
        latency_ms=2.0,
        fps=500.0,
        success_rate=1.0,
        memory_mb=64.0,
        cpu_utilization_percent=80.0,
        stage_latencies_ms={"detector": 1.5, "pnp": 0.5},
        accuracy_metrics={"mean_reprojection_error_px": 0.2},
        software_versions={"opencv": "4.x"},
    )
    document = result.to_dict()
    assert document["gpu"] is None
    assert document["image_resolution"] == {"width_px": 640, "height_px": 480}
    assert document["cpu_utilization_percent"] == 80.0
    assert document["stage_latencies_ms"] == {"detector": 1.5, "pnp": 0.5}
    with pytest.raises(ValueError, match="success rate"):
        VisionBenchmarkResult(
            host="host",
            cpu="cpu",
            gpu=None,
            source_type="synthetic",
            image_size=ImageSize(1, 1),
            algorithm="algorithm",
            latency_ms=1.0,
            fps=1.0,
            success_rate=1.1,
        )
