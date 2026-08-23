import json
import os
import subprocess
import sys

import numpy as np

from applications.vision_lab.mock_guidance import main


def test_mock_guidance_output(capsys) -> None:
    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["job_state"] == "COMPLETED"
    assert payload["robot_command_id"] == "mock-0001"
    assert payload["hardware_validated"] is False
    assert np.allclose(payload["target_position_m"], [0.6, 0.2, 0.4])


def test_mock_guidance_module_smoke() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, ["src", environment.get("PYTHONPATH", "")]))
    result = subprocess.run(
        [sys.executable, "-m", "applications.vision_lab.mock_guidance"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["job_state"] == "COMPLETED"
