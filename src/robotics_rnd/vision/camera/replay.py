"""Deterministic in-memory image replay independent of capture formats."""

from __future__ import annotations

from collections.abc import Iterable

from .sources import ImageFrame


class ImageSequenceSource:
    def __init__(self, frames: Iterable[ImageFrame]) -> None:
        self._frames = tuple(frames)
        if not self._frames:
            raise ValueError("image replay requires at least one frame")
        self._cursor = 0

    @property
    def remaining(self) -> int:
        return len(self._frames) - self._cursor

    def reset(self) -> None:
        self._cursor = 0

    def read(self) -> ImageFrame:
        if self._cursor >= len(self._frames):
            raise StopIteration("image sequence exhausted")
        frame = self._frames[self._cursor]
        self._cursor += 1
        return frame
