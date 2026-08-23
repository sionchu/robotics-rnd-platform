import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("command", ["calibration", "apriltag", "pnp"])
def test_vision_cli_smoke(command: str) -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, ["src", environment.get("PYTHONPATH", "")]))
    result = subprocess.run(
        [sys.executable, "-m", "robotics_rnd.vision", command],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["synthetic_only"] is True


def test_calibration_cli_writes_portable_json(tmp_path: Path) -> None:
    output = tmp_path / "camera.json"
    result = subprocess.run(
        [sys.executable, "-m", "robotics_rnd.vision", "calibration", "--output", str(output)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["schema"] == "robotics-rnd-camera-calibration-v1"
    assert document["units"] == {"image": "pixels", "target_lengths": "metres"}
