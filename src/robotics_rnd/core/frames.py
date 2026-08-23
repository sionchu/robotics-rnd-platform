"""Validated coordinate-frame identifiers."""

from __future__ import annotations

import re
from dataclasses import dataclass

_FRAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_./-]*$")


@dataclass(frozen=True, slots=True, order=True)
class FrameId:
    """A non-empty, portable frame name with no implicit vendor meaning."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not _FRAME_PATTERN.fullmatch(self.value):
            raise ValueError(
                "frame id must start with a letter and contain only letters, digits, '_', '.', '/', or '-'"
            )

    def __str__(self) -> str:
        return self.value
