"""Hardware-free RB Control Lab CLI; deliberately exposes no live command path."""

from __future__ import annotations

import argparse
import json
from importlib import metadata
from pathlib import Path
from typing import Any

from robotics_rnd.drivers.rainbow import FakeRainbowBackend, RainbowConfig, RainbowRobotDriver
from robotics_rnd.rb_lab import run_fault_demo, run_mock_demo, run_replay_demo


def _status() -> dict[str, Any]:
    try:
        rbpodo_version = metadata.version("rbpodo")
    except metadata.PackageNotFoundError:
        rbpodo_version = "not-installed"
    return {
        "status": "SOFTWARE_VALIDATED",
        "hardware_validation": False,
        "max_hardware_validation_level": 0,
        "rbpodo_installed_version": rbpodo_version,
        "live_commands_available": False,
    }


def _capabilities() -> dict[str, Any]:
    robot = RainbowRobotDriver(RainbowConfig(), FakeRainbowBackend())
    return {
        "operation_mode": "READ_ONLY",
        "capabilities": sorted(capability.value for capability in robot.capabilities),
        "motion_enabled": False,
        "io_write_enabled": False,
        "hardware_validation": False,
        "max_hardware_validation_level": 0,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="show software and hardware-validation status")
    commands.add_parser("capabilities", help="show the default read-only capability boundary")
    mock = commands.add_parser("mock-demo", help="run fake adapter, journal, and replay")
    mock.add_argument("--journal", type=Path, default=Path("/tmp/robotics-rnd-rb-mock-demo.jsonl"))
    commands.add_parser("fault-demo", help="inject a connection drop and prove motion lockout")
    replay = commands.add_parser("replay", help="inspect a platform JSONL journal")
    replay.add_argument("journal", type=Path)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    if arguments.command == "status":
        result = _status()
    elif arguments.command == "capabilities":
        result = _capabilities()
    elif arguments.command == "mock-demo":
        result = run_mock_demo(arguments.journal)
    elif arguments.command == "fault-demo":
        result = run_fault_demo()
    else:
        result = run_replay_demo(arguments.journal)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
