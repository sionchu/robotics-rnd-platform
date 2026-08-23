"""Small generic research and workflow models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import isfinite
from types import MappingProxyType
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class QualityMetric:
    name: str
    value: float
    unit: str = "1"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("quality metric name is required")
        if not isfinite(self.value):
            raise ValueError("quality metric value must be finite")


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    name: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_id.strip() or not self.name.strip():
            raise ValueError("task id and name are required")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class Job:
    job_id: str
    name: str
    tasks: tuple[Task, ...]
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.job_id.strip() or not self.name.strip():
            raise ValueError("job id and name are required")
        if self.created_at.tzinfo is None:
            raise ValueError("job timestamp must be timezone-aware")
        task_ids = [task.task_id for task in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("task ids must be unique within a job")
