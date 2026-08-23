"""Verify v0.2.1 Pi camera experiment preparation without fabricating hardware data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = (
    "006_pi_camera_bringup",
    "007_pi_camera_calibration",
    "008_pi_apriltag_repeatability",
    "009_pi_distance_sensitivity",
    "010_pi_angle_sensitivity",
    "011_pi_capture_conditions",
    "012_pi_vs_laptop_benchmark",
)
REQUIRED_HEADINGS = (
    "## Question",
    "## Hypothesis",
    "## Hardware",
    "## Software",
    "## Method",
    "## Ground truth class",
    "## Measurement uncertainty",
    "## Results",
    "## Failure cases",
    "## Limitations",
    "## Conclusion",
    "## Decision",
)


def verify_preparation() -> dict[str, object]:
    records: dict[str, object] = {}
    for name in EXPERIMENTS:
        root = ROOT / "experiments/vision" / name
        required = (
            root / "README.md",
            root / "config/config.json",
            root / "results/README.md",
            root / "results/status.json",
            root / "conclusion.md",
        )
        missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(f"{name} preparation is incomplete: {missing}")
        conclusion = (root / "conclusion.md").read_text(encoding="utf-8")
        absent_headings = [heading for heading in REQUIRED_HEADINGS if heading not in conclusion]
        if absent_headings:
            raise RuntimeError(f"{name} conclusion is missing headings: {absent_headings}")
        status = json.loads((root / "results/status.json").read_text(encoding="utf-8"))
        if status.get("schema") != "robotics-rnd-hardware-experiment-status-v1":
            raise RuntimeError(f"{name} has an unsupported result schema")
        if status.get("status") != "NOT_RUN_HARDWARE_UNAVAILABLE":
            raise RuntimeError(f"{name} must remain not-run until physical evidence exists")
        if status.get("hardware_validated") is not False or status.get("measurements") is not None:
            raise RuntimeError(f"{name} contains fabricated or inconsistent hardware evidence")
        records[name] = {
            "status": status["status"],
            "decision": status["decision"],
            "prepared": True,
        }
    return {
        "milestone": "v0.2.1-pi-camera-edge-lab",
        "hardware_reachable": False,
        "release_tag_allowed": False,
        "experiments": records,
        "acceptance": {
            "all_experiments_prepared": len(records) == len(EXPERIMENTS),
            "no_fabricated_measurements": True,
            "hardware_handoff_required": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify-preparation",))
    parser.parse_args()
    print(json.dumps(verify_preparation(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
