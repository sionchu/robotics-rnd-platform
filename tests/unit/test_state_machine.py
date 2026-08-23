import pytest

from robotics_rnd.core.state_machine import InvalidTransition, JobEvent, JobState, build_job_state_machine


def test_valid_job_lifecycle() -> None:
    machine = build_job_state_machine()
    for event in (JobEvent.CONNECT, JobEvent.CONNECTION_READY, JobEvent.START, JobEvent.SUCCEED):
        machine.trigger(event)
    assert machine.state is JobState.COMPLETED
    assert len(machine.history) == 4


def test_invalid_transition_is_explicit() -> None:
    machine = build_job_state_machine()
    with pytest.raises(InvalidTransition, match="invalid"):
        machine.trigger(JobEvent.START)


def test_fault_and_recovery() -> None:
    machine = build_job_state_machine()
    machine.trigger(JobEvent.CONNECT)
    machine.trigger(JobEvent.FAIL)
    assert machine.state is JobState.FAULT
    machine.trigger(JobEvent.RESET)
    assert machine.state is JobState.IDLE


def test_stop_and_recovery() -> None:
    machine = build_job_state_machine()
    machine.trigger(JobEvent.CONNECT)
    machine.trigger(JobEvent.CONNECTION_READY)
    machine.trigger(JobEvent.STOP)
    assert machine.state is JobState.STOPPED
    machine.trigger(JobEvent.RESET)
    assert machine.state is JobState.IDLE
