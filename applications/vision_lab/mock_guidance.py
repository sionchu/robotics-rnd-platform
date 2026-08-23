"""Run one deterministic mock vision-guidance cycle."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from robotics_rnd.core import FrameId, QualityMetric
from robotics_rnd.core.geometry import Pose, Quaternion, Transform, Vector3
from robotics_rnd.drivers.mock import MockRobot, MockVision
from robotics_rnd.skills.robot_guidance import MockGuidanceJob
from robotics_rnd.vision import VisionObservation, VisionTarget


def main() -> int:
    camera = FrameId("camera")
    base = FrameId("robot_base")
    target = VisionTarget(
        "generic_target",
        Pose(Vector3(0.10, 0.20, 0.30), Quaternion.identity(), camera),
        confidence=0.95,
        quality=(QualityMetric("synthetic_confidence", 0.95),),
    )
    observation = VisionObservation(
        "mock-observation-001",
        datetime(2026, 1, 1, tzinfo=UTC),
        camera,
        targets=(target,),
        metadata={"source": "deterministic_mock"},
    )
    camera_to_base = Transform(base, camera, Vector3(0.50, 0.0, 0.10), Quaternion.identity())
    run = MockGuidanceJob(MockRobot(base_frame=base), MockVision((observation,)), camera_to_base).run()
    payload = {
        "job_state": run.final_state.value,
        "observation_id": run.observation.observation_id,
        "robot_command_id": run.robot_result.command_id,
        "target_position_m": run.robot_result.state.tool_pose.position_m.as_array().tolist(),
        "hardware_validated": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
