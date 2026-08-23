from __future__ import annotations

import pytest

from robotics_rnd.vision.edge_analysis import (
    PoseFrameSample,
    analyze_pose_repeatability,
    compare_pose_runs,
)


def sample(index: int, x: float, *, detected: bool = True) -> PoseFrameSample:
    if not detected:
        return PoseFrameSample(index, 1_000_000_000 + index * 10_000_000, False)
    return PoseFrameSample(
        index,
        1_000_000_000 + index * 10_000_000,
        True,
        translation_m=(x, 0.0, 1.0),
        quaternion_xyzw=(0.0, 0.0, 0.0, 1.0),
        corner_pixels=((0.0 + x, 0.0), (1.0 + x, 0.0), (1.0 + x, 1.0), (0.0 + x, 1.0)),
        mean_reprojection_error_px=0.2,
    )


def test_repeatability_reports_detection_pose_corner_and_timing_metrics() -> None:
    metrics = analyze_pose_repeatability((sample(0, 0.0), sample(1, 0.01), sample(2, 0.0, detected=False)))
    assert metrics["detection_success_rate"] == pytest.approx(2 / 3)
    assert metrics["translation_rms_jitter_m"] == pytest.approx(0.005)
    assert metrics["orientation_mean_deviation_deg"] == 0.0
    assert metrics["corner_rms_jitter_px"] == pytest.approx(0.005)
    assert metrics["frame_interval_mean_ms"] == pytest.approx(10.0)


def test_pose_run_comparison_and_order_validation() -> None:
    reference = (sample(0, 0.0), sample(1, 0.01))
    comparison = compare_pose_runs(reference, (sample(0, 0.001), sample(1, 0.011)))
    assert comparison["detection_disagreements"] == 0
    assert comparison["max_translation_delta_m"] == pytest.approx(0.001)
    with pytest.raises(ValueError, match="same frame count"):
        compare_pose_runs(reference, reference[:1])
    with pytest.raises(ValueError, match="ordered sequence"):
        analyze_pose_repeatability((sample(1, 0.0), sample(0, 0.0)))
