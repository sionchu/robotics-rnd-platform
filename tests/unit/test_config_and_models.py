from datetime import datetime

import pytest

from robotics_rnd.core import DiagnosticStatus, FrameId, Job, QualityMetric, Severity, Task
from robotics_rnd.core.config import load_config


def test_config_load_and_unknown_key(tmp_path) -> None:
    config_path = tmp_path / "platform.toml"
    config_path.write_text('[platform]\ndefault_frame="map"\nlog_level="debug"\ndry_run=true\n')
    config = load_config(config_path)
    assert config.default_frame == FrameId("map")
    assert config.log_level == "DEBUG"
    bad_path = tmp_path / "bad.toml"
    bad_path.write_text("[platform]\nunknown=true\n")
    with pytest.raises(ValueError, match="unknown"):
        load_config(bad_path)


def test_quality_diagnostics_and_job_validation() -> None:
    assert QualityMetric("confidence", 0.9).unit == "1"
    with pytest.raises(ValueError, match="finite"):
        QualityMetric("confidence", float("nan"))
    diagnostic = DiagnosticStatus("camera", Severity.WARNING, "offline", {"action": "use replay"})
    assert diagnostic.details["action"] == "use replay"
    task = Task("task-1", "observe")
    with pytest.raises(ValueError, match="timezone-aware"):
        Job("job-1", "demo", (task,), created_at=datetime(2026, 1, 1))
    with pytest.raises(ValueError, match="unique"):
        Job("job-1", "demo", (task, task))
