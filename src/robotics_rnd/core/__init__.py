"""Stable, vendor-independent platform primitives."""

from .diagnostics import DiagnosticStatus, Severity
from .frames import FrameId
from .models import Job, QualityMetric, Task

__all__ = ["DiagnosticStatus", "FrameId", "Job", "QualityMetric", "Severity", "Task"]
