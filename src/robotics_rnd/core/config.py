"""Minimal validated configuration using Python's TOML reader."""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .frames import FrameId


@dataclass(frozen=True, slots=True)
class PlatformConfig:
    default_frame: FrameId = field(default_factory=lambda: FrameId("world"))
    log_level: str = "INFO"
    dry_run: bool = True

    def __post_init__(self) -> None:
        level = self.log_level.upper()
        if level not in logging.getLevelNamesMapping():
            raise ValueError(f"invalid log level: {self.log_level}")
        object.__setattr__(self, "log_level", level)


def load_config(path: Path) -> PlatformConfig:
    """Load `[platform]` values without adding a YAML dependency to core."""

    with path.open("rb") as stream:
        document = tomllib.load(stream)
    values = document.get("platform", {})
    if not isinstance(values, dict):
        raise ValueError("[platform] must be a TOML table")
    allowed = {"default_frame", "log_level", "dry_run"}
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(f"unknown platform config keys: {sorted(unknown)}")
    return PlatformConfig(
        default_frame=FrameId(str(values.get("default_frame", "world"))),
        log_level=str(values.get("log_level", "INFO")),
        dry_run=values.get("dry_run", True),
    )
