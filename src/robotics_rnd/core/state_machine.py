"""Deterministic generic state transitions and a reusable job lifecycle."""

from __future__ import annotations

from collections.abc import Hashable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class InvalidTransition(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Transition[StateT: Hashable, EventT: Hashable]:
    source: StateT
    event: EventT
    target: StateT


@dataclass(frozen=True, slots=True)
class TransitionRecord[StateT: Hashable, EventT: Hashable]:
    transition: Transition[StateT, EventT]
    timestamp: datetime


class StateMachine[StateT: Hashable, EventT: Hashable]:
    def __init__(self, initial: StateT, transitions: Iterable[Transition[StateT, EventT]]) -> None:
        self._state = initial
        self._transitions: dict[tuple[StateT, EventT], Transition[StateT, EventT]] = {}
        self._history: list[TransitionRecord[StateT, EventT]] = []
        for transition in transitions:
            key = (transition.source, transition.event)
            if key in self._transitions:
                raise ValueError(f"duplicate transition for {key!r}")
            self._transitions[key] = transition

    @property
    def state(self) -> StateT:
        return self._state

    @property
    def history(self) -> tuple[TransitionRecord[StateT, EventT], ...]:
        return tuple(self._history)

    def can_trigger(self, event: EventT) -> bool:
        return (self._state, event) in self._transitions

    def trigger(self, event: EventT) -> StateT:
        transition = self._transitions.get((self._state, event))
        if transition is None:
            raise InvalidTransition(f"event {event!r} is invalid from state {self._state!r}")
        self._state = transition.target
        self._history.append(TransitionRecord(transition, datetime.now(UTC)))
        return self._state


class JobState(StrEnum):
    IDLE = "IDLE"
    CONNECTING = "CONNECTING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAULT = "FAULT"
    STOPPED = "STOPPED"


class JobEvent(StrEnum):
    CONNECT = "CONNECT"
    CONNECTION_READY = "CONNECTION_READY"
    START = "START"
    SUCCEED = "SUCCEED"
    FAIL = "FAIL"
    STOP = "STOP"
    RESET = "RESET"


def build_job_state_machine() -> StateMachine[JobState, JobEvent]:
    transitions = [
        Transition(JobState.IDLE, JobEvent.CONNECT, JobState.CONNECTING),
        Transition(JobState.CONNECTING, JobEvent.CONNECTION_READY, JobState.READY),
        Transition(JobState.READY, JobEvent.START, JobState.RUNNING),
        Transition(JobState.RUNNING, JobEvent.SUCCEED, JobState.COMPLETED),
    ]
    transitions.extend(
        Transition(state, JobEvent.FAIL, JobState.FAULT)
        for state in (JobState.IDLE, JobState.CONNECTING, JobState.READY, JobState.RUNNING)
    )
    transitions.extend(
        Transition(state, JobEvent.STOP, JobState.STOPPED)
        for state in (JobState.CONNECTING, JobState.READY, JobState.RUNNING)
    )
    transitions.extend(
        Transition(state, JobEvent.RESET, JobState.IDLE)
        for state in (JobState.COMPLETED, JobState.FAULT, JobState.STOPPED)
    )
    return StateMachine(JobState.IDLE, transitions)
