from __future__ import annotations

from pathlib import Path

from robotics_rnd.drivers.mock import MockRobot
from robotics_rnd.drivers.replay import ReplayRobot
from robotics_rnd.robot import RobotApplicationService, RobotCommand, RobotJournal, read_journal


def _create_journal(path: Path) -> tuple[RobotCommand, str]:
    command = RobotCommand.move_joint((0.1,) * 6, command_id="portable-command-001")
    service = RobotApplicationService(MockRobot(), RobotJournal(path, "portable-session"))
    service.connect()
    result = service.execute(command)
    service.disconnect()
    assert result.command_id is not None
    return command, result.command_id


def test_journal_round_trip_and_replay(tmp_path: Path) -> None:
    path = tmp_path / "session.jsonl"
    command, command_id = _create_journal(path)
    records = list(read_journal(path))
    assert [record.sequence for record in records] == list(range(1, len(records) + 1))
    assert {record.event_type for record in records} >= {
        "command_submitted",
        "command_transition",
        "command_result",
        "state",
    }
    transitions = [record for record in records if record.event_type == "command_transition"]
    assert [record.payload["status"] for record in transitions] == ["SUBMITTED", "COMPLETED"]
    replay = ReplayRobot(path)
    assert replay.connect().success
    result = replay.execute(command)
    assert result.command_id == command_id
    assert result.state.joints.positions_rad == (0.1,) * 6
    assert replay.remaining == 0


def test_application_service_runs_against_replay(tmp_path: Path) -> None:
    path = tmp_path / "application-replay.jsonl"
    command, _ = _create_journal(path)
    service = RobotApplicationService(ReplayRobot(path))
    assert service.connect().success
    assert service.execute(command).success
    assert service.disconnect().success


def test_journal_redacts_sensitive_fields(tmp_path: Path) -> None:
    path = tmp_path / "redacted.jsonl"
    journal = RobotJournal(path, "redaction-test")
    journal.append(
        "configuration",
        {
            "host": "sensitive-value-alpha",
            "api_token": "sensitive-value-beta",
            "nested": {"controller_address": "sensitive-value-gamma", "safe": "visible"},
        },
    )
    text = path.read_text(encoding="utf-8")
    assert "sensitive-value-alpha" not in text
    assert "sensitive-value-beta" not in text
    assert "sensitive-value-gamma" not in text
    assert '"safe":"visible"' in text


def test_application_service_emits_backend_independent_events(tmp_path: Path) -> None:
    events = []
    service = RobotApplicationService(MockRobot(), RobotJournal(tmp_path / "events.jsonl", "events"))
    service.subscribe(events.append)
    service.connect()
    service.execute(RobotCommand.write_digital_output(0, True))
    service.disconnect()
    assert [event.event_type for event in events] == ["connected", "command_result", "disconnected"]
    assert events[1].command_id == "session-0001"
