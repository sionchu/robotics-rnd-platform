"""Generic image-source boundary for synthetic, replay, and future cameras."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from robotics_rnd.core import FrameId

from .models import ImageSize


@dataclass(frozen=True, slots=True)
class ImageFrame:
    frame_id: FrameId
    timestamp: datetime
    image: NDArray[np.uint8]
    source_id: str

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("image timestamp must be timezone-aware")
        if not self.source_id.strip():
            raise ValueError("image source id is required")
        image = np.asarray(self.image)
        if image.dtype != np.uint8 or image.ndim not in (2, 3):
            raise ValueError("image must be a uint8 grayscale or color array")
        if image.ndim == 3 and image.shape[2] not in (3, 4):
            raise ValueError("color image must have three or four channels")
        copy = image.copy()
        copy.flags.writeable = False
        object.__setattr__(self, "image", copy)

    @property
    def image_size(self) -> ImageSize:
        return ImageSize(width_px=int(self.image.shape[1]), height_px=int(self.image.shape[0]))


class ImageSource(Protocol):
    def read(self) -> ImageFrame:
        """Return the next image or raise `StopIteration` when exhausted."""
