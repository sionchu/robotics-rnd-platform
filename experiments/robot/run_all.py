"""Reproduce the four hardware-free v0.3 RB control experiments."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from robotics_rnd.core import FrameId
from robotics_rnd.drivers.rainbow import (
    FakeRainbowBackend,
    FaultScenario,
    RainbowConfig,
    RainbowOperationMode,
    RainbowRobotDriver,
)
from robotics_rnd.drivers.rainbow.mapping import (
    equivalent_euler_rotation,
    platform_pose_to_vendor,
    vendor_pose_to_platform,
)
from robotics_rnd.robot import CommandStatus, ConnectionState, RobotCommand

ROOT = Path(__file__).resolve().parents[2]
WRITE_RESULTS = True


def write_json(path: Path, document: Any) -> None:
    if not WRITE_RESULTS:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fake_driver(
    *faults: FaultScenario, motion: bool = True, io_write: bool = True
) -> tuple[RainbowRobotDriver, FakeRainbowBackend]:
    backend = FakeRainbowBackend(faults)
    driver = RainbowRobotDriver(
        RainbowConfig(
            operation_mode=RainbowOperationMode.FAKE,
            motion_enabled=motion,
            io_write_enabled=io_write,
        ),
        backend,
    )
    return driver, backend


def run_pose_mapping() -> dict[str, Any]:
    output = ROOT / "experiments/robot/013_rb_pose_mapping/results/metrics.json"
    frame = FrameId("robot_base")
    cases = (
        ("zero", (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
        ("translation", (100.0, -200.0, 300.0, 0.0, 0.0, 0.0)),
        ("rotate_x", (0.0, 0.0, 0.0, 90.0, 0.0, 0.0)),
        ("rotate_y", (0.0, 0.0, 0.0, 0.0, -45.0, 0.0)),
        ("rotate_z", (0.0, 0.0, 0.0, 0.0, 0.0, 170.0)),
        ("combined", (125.0, 20.0, -55.0, 20.0, -35.0, 70.0)),
        ("gimbal_positive", (0.0, 0.0, 0.0, 20.0, 90.0, 40.0)),
        ("gimbal_negative", (0.0, 0.0, 0.0, -20.0, -90.0, 40.0)),
    )
    records: list[dict[str, Any]] = []
    for name, source in cases:
        pose = vendor_pose_to_platform(source, frame)
        mapped = platform_pose_to_vendor(pose, frame)
        translation_error_mm = float(np.max(np.abs(np.asarray(source[:3]) - np.asarray(mapped[:3]))))
        rotation_matches = equivalent_euler_rotation(source[3:], mapped[3:], tolerance=1e-8)
        records.append(
            {
                "case": name,
                "translation_error_mm": translation_error_mm,
                "rotation_matrix_matches": rotation_matches,
            }
        )
    invalid_rejected = False
    try:
        vendor_pose_to_platform((float("nan"), 0.0, 0.0, 0.0, 0.0, 0.0), frame)
    except ValueError:
        invalid_rejected = True
    acceptance = {
        "all_rotation_round_trips_match": all(row["rotation_matrix_matches"] for row in records),
        "max_translation_error_below_1e_9_mm": max(float(row["translation_error_mm"]) for row in records)
        < 1e-9,
        "invalid_values_rejected": invalid_rejected,
    }
    metrics = {
        "experiment": "013_rb_pose_mapping",
        "evidence_class": ["SOURCE_VERIFIED", "MOCK_VERIFIED"],
        "hardware_validation": False,
        "max_hardware_validation_level": 0,
        "vendor_convention": "[x_mm,y_mm,z_mm,rx_deg,ry_deg,rz_deg], Rz@Ry@Rx",
        "platform_convention": "metres, XYZW unit quaternion, explicit parent frame",
        "cases": records,
        "acceptance": acceptance,
        "decision": "PROMOTE_TO_PLATFORM",
    }
    write_json(output, metrics)
    if not all(acceptance.values()):
        raise RuntimeError("RB pose-mapping acceptance gate failed")
    return metrics


def run_command_semantics() -> dict[str, Any]:
    output = ROOT / "experiments/robot/014_rbpodo_command_semantics/results/metrics.json"
    completed_driver, _ = fake_driver()
    completed_driver.connect()
    completed = completed_driver.execute(RobotCommand.move_joint((0.0,) * 6))
    timeout_driver, _ = fake_driver(FaultScenario.MOTION_TIMEOUT)
    timeout_driver.connect()
    timed_out = timeout_driver.execute(RobotCommand.move_joint((0.0,) * 6))
    stale_driver, _ = fake_driver(
        FaultScenario.DELAYED_RESPONSE,
        FaultScenario.DUPLICATE_RESPONSE,
        FaultScenario.UNEXPECTED_RESPONSE,
    )
    stale_driver.connect()
    anomalies = stale_driver.execute(RobotCommand.move_joint((0.0,) * 6))
    assert completed.status is not None
    assert timed_out.status is not None
    assert anomalies.diagnostics is not None
    acceptance = {
        "completed_requires_completion_evidence": completed.status is CommandStatus.COMPLETED,
        "accepted_timeout_not_completed": timed_out.status is CommandStatus.TIMED_OUT,
        "response_anomalies_recorded": len(anomalies.diagnostics["backend_events"]) == 3,
    }
    metrics = {
        "experiment": "014_rbpodo_command_semantics",
        "evidence_class": ["SOURCE_VERIFIED", "MOCK_VERIFIED"],
        "live_verified": False,
        "hardware_validation": False,
        "max_hardware_validation_level": 0,
        "source_findings": {
            "ack_meaning": "command received/executed acknowledgement; not motion completion",
            "completion_signal": "motion_changed start/finish broadcast messages",
            "response_buffer_rule": "flush before command/wait to avoid stale messages",
            "multiple_clients": "broadcast responses may include unrelated client errors",
        },
        "mock_statuses": {
            "normal": completed.status.value,
            "motion_timeout": timed_out.status.value,
            "anomaly_diagnostics": anomalies.diagnostics["backend_events"],
        },
        "acceptance": acceptance,
        "decision": "PROMOTE_TO_PLATFORM",
    }
    write_json(output, metrics)
    if not all(acceptance.values()):
        raise RuntimeError("rbpodo command-semantics acceptance gate failed")
    return metrics


def run_fault_reconnect() -> dict[str, Any]:
    output = ROOT / "experiments/robot/015_rb_fault_reconnect/results/metrics.json"
    connect_failure, _ = fake_driver(FaultScenario.CONNECT_TIMEOUT)
    connect_result = connect_failure.connect()
    driver, backend = fake_driver(FaultScenario.CONNECTION_DROP_DURING_COMMAND)
    driver.connect()
    uncertain = driver.execute(RobotCommand.move_joint((0.1,) * 6))
    reconnect = driver.reconnect()
    blocked = driver.execute(RobotCommand.move_joint((0.0,) * 6))
    no_resume_before_ack = not any("resume" in call for call in backend.calls)
    driver.acknowledge_resync()
    recovered = driver.execute(RobotCommand.move_joint((0.0,) * 6))
    backend.inject(FaultScenario.STALE_STATE)
    stale = driver.get_state()
    assert uncertain.status is not None
    assert recovered.status is not None
    assert stale.connection_state is not None
    acceptance = {
        "connect_failure_not_connected": not connect_result.state.connected,
        "ambiguous_command_is_unknown": uncertain.status is CommandStatus.UNKNOWN,
        "reconnect_state_synchronized": reconnect.success,
        "motion_locked_until_acknowledged": blocked.error_code == "RESYNC_REQUIRED",
        "no_automatic_resume": no_resume_before_ack,
        "explicit_ack_allows_new_command": recovered.status is CommandStatus.COMPLETED,
        "stale_state_degrades_connection": stale.connection_state is ConnectionState.DEGRADED,
    }
    metrics = {
        "experiment": "015_rb_fault_reconnect",
        "evidence_class": ["MOCK_VERIFIED"],
        "hardware_validation": False,
        "max_hardware_validation_level": 0,
        "observed": {
            "connect_failure_code": connect_result.error_code,
            "ambiguous_command_status": uncertain.status.value,
            "blocked_command_code": blocked.error_code,
            "recovered_status": recovered.status.value,
            "stale_connection_state": stale.connection_state.value,
        },
        "acceptance": acceptance,
        "decision": "PROMOTE_TO_PLATFORM",
    }
    write_json(output, metrics)
    if not all(acceptance.values()):
        raise RuntimeError("RB fault/reconnect acceptance gate failed")
    return metrics


def run_io_contract() -> dict[str, Any]:
    output = ROOT / "experiments/robot/016_rb_io_contract/results/metrics.json"
    driver, backend = fake_driver()
    driver.connect()
    results = [driver.write_digital_output(channel, channel % 2 == 0) for channel in range(16)]
    invalid = driver.write_digital_output(16, True)
    state = driver.get_state()
    read_only, _ = fake_driver(motion=False, io_write=False)
    acceptance = {
        "all_control_box_channels_round_trip": all(
            result.success and state.digital_outputs[channel] is (channel % 2 == 0)
            for channel, result in enumerate(results)
        ),
        "zero_based_channel_16_rejected": invalid.error_code == "INVALID_CHANNEL",
        "read_only_does_not_claim_output": "DIGITAL_OUTPUT"
        not in {capability.value for capability in read_only.capabilities},
        "no_tool_io_claim": "TOOL_IO" not in {capability.value for capability in driver.capabilities},
        "fake_backend_received_16_valid_writes": sum(
            call.startswith("write_digital_output") for call in backend.calls
        )
        == 17,
    }
    metrics = {
        "experiment": "016_rb_io_contract",
        "evidence_class": ["SOURCE_VERIFIED", "MOCK_VERIFIED"],
        "hardware_validation": False,
        "max_hardware_validation_level": 0,
        "source_findings": {
            "control_box_digital_inputs": 16,
            "control_box_digital_outputs": 16,
            "indexing": "0..15",
            "tool_io": "model-dependent; not promoted as generic Rainbow capability",
        },
        "acceptance": acceptance,
        "decision": "PROMOTE_TO_PLATFORM",
    }
    write_json(output, metrics)
    if not all(acceptance.values()):
        raise RuntimeError("RB I/O acceptance gate failed")
    return metrics


RUNNERS: dict[str, Callable[[], dict[str, Any]]] = {
    "pose": run_pose_mapping,
    "semantics": run_command_semantics,
    "reconnect": run_fault_reconnect,
    "io": run_io_contract,
}


def main() -> int:
    global WRITE_RESULTS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", choices=(*RUNNERS, "all", "verify"))
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="run all calculations and gates without rewriting tracked results",
    )
    arguments = parser.parse_args()
    WRITE_RESULTS = not arguments.verify_only and arguments.experiment != "verify"
    selected = (
        RUNNERS
        if arguments.experiment in {"all", "verify"}
        else {arguments.experiment: RUNNERS[arguments.experiment]}
    )
    summaries: dict[str, Any] = {}
    for name, runner in selected.items():
        result = runner()
        summaries[name] = {"acceptance": result["acceptance"], "decision": result["decision"]}
    print(json.dumps(summaries, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
