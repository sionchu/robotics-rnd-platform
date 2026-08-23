"""Structured diagnostic values and the package doctor entry point."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import IntEnum
from types import MappingProxyType


class Severity(IntEnum):
    OK = 0
    INFO = 1
    WARNING = 2
    ERROR = 3


@dataclass(frozen=True, slots=True)
class DiagnosticStatus:
    component: str
    severity: Severity
    message: str
    details: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.component.strip() or not self.message.strip():
            raise ValueError("diagnostic component and message are required")
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))


def main() -> int:
    import runpy
    from pathlib import Path

    script = Path(__file__).resolve().parents[3] / "scripts" / "doctor.py"
    runpy.run_path(str(script), run_name="__main__")
    return 0
