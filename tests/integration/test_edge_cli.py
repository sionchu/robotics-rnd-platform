from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path

import pytest


def test_edge_cli_help_is_hardware_independent() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "robotics_rnd.edge", "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "capture" in result.stdout
    assert "calibrate-dataset" in result.stdout
    assert "compare-runs" in result.stdout


def test_capture_cli_fails_actionably_without_pi_hardware(tmp_path: Path) -> None:
    if platform.machine().lower() in {"aarch64", "arm64"}:
        pytest.skip("non-Pi CLI failure path is specific to x86 CI")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "robotics_rnd.edge",
            "capture",
            "--output",
            str(tmp_path / "capture"),
            "--frames",
            "1",
            "--minimum-free-mb",
            "0",
            "--camera-mode",
            "unvalidated-test-mode",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    payload = json.loads(result.stderr)
    assert payload["status"] == "ERROR"
    assert "requires Raspberry Pi ARM64" in payload["message"]
    assert "hardware_validated" not in payload
