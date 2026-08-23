#!/usr/bin/env python3
"""Aggregate physical pose-run summaries and optionally plot one study factor."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def load_row(factor: str, specification: str) -> dict[str, Any]:
    if "=" not in specification:
        raise ValueError("each --run must be FACTOR_VALUE=POSE_RUN_JSON")
    value, path_text = specification.split("=", 1)
    document = json.loads(Path(path_text).read_text(encoding="utf-8"))
    if document.get("schema") != "robotics-rnd-edge-pose-run-v1":
        raise ValueError(f"unsupported pose-run schema: {path_text}")
    metrics = document["repeatability"]
    return {
        factor: value,
        "dataset_id": document["dataset_id"],
        "ground_truth_class": document["ground_truth_class"],
        "frames": metrics["frames"],
        "detection_success_rate": metrics["detection_success_rate"],
        "translation_rms_jitter_mm": (
            metrics["translation_rms_jitter_m"] * 1_000.0
            if metrics["translation_rms_jitter_m"] is not None
            else None
        ),
        "orientation_std_deviation_deg": metrics["orientation_std_deviation_deg"],
        "corner_rms_jitter_px": metrics["corner_rms_jitter_px"],
        "mean_reprojection_error_px": metrics["mean_reprojection_error_px"],
        "frame_interval_mean_ms": metrics["frame_interval_mean_ms"],
        "frame_interval_std_ms": metrics["frame_interval_std_ms"],
    }


def write_plot(rows: list[dict[str, Any]], factor: str, output: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required only when --plot is requested") from exc
    x = [row[factor] for row in rows]
    figure, axes = plt.subplots(3, 1, figsize=(8, 9), constrained_layout=True)
    axes[0].plot(x, [row["detection_success_rate"] for row in rows], marker="o")
    axes[0].set_ylabel("Detection success [0-1]")
    axes[1].plot(x, [row["translation_rms_jitter_mm"] for row in rows], marker="o")
    axes[1].set_ylabel("Translation RMS jitter [mm]")
    axes[2].plot(x, [row["orientation_std_deviation_deg"] for row in rows], marker="o")
    axes[2].set_ylabel("Orientation deviation std [deg]")
    axes[2].set_xlabel(factor)
    for axis in axes:
        axis.grid(True, alpha=0.3)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=150)
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--factor", required=True)
    parser.add_argument("--run", action="append", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--plot", type=Path)
    arguments = parser.parse_args()
    rows = [load_row(arguments.factor, specification) for specification in arguments.run]
    payload = {
        "schema": "robotics-rnd-physical-study-summary-v1",
        "factor": arguments.factor,
        "rows": rows,
    }
    arguments.output_json.parent.mkdir(parents=True, exist_ok=True)
    arguments.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    arguments.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    if arguments.plot is not None:
        write_plot(rows, arguments.factor, arguments.plot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
