from datetime import UTC, datetime

import pytest

from robotics_rnd.robot import (
    CommandLifecycleEvent,
    CommandStatus,
    StatusEvidence,
    validate_command_transition,
)


def test_acknowledgement_and_completion_are_distinct_lifecycle_states() -> None:
    validate_command_transition(CommandStatus.SUBMITTED, CommandStatus.ACCEPTED)
    validate_command_transition(CommandStatus.ACCEPTED, CommandStatus.RUNNING)
    validate_command_transition(CommandStatus.RUNNING, CommandStatus.COMPLETED)


def test_terminal_status_cannot_transition_back_to_running() -> None:
    with pytest.raises(ValueError, match="invalid command transition"):
        validate_command_transition(CommandStatus.COMPLETED, CommandStatus.RUNNING)


def test_lifecycle_event_requires_timezone_and_id() -> None:
    event = CommandLifecycleEvent(
        "command-001",
        CommandStatus.ACCEPTED,
        StatusEvidence.VENDOR_REPORTED,
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert event.status is CommandStatus.ACCEPTED
    with pytest.raises(ValueError, match="timezone"):
        CommandLifecycleEvent(
            "command-001",
            CommandStatus.ACCEPTED,
            StatusEvidence.VENDOR_REPORTED,
            datetime(2026, 1, 1),
        )
