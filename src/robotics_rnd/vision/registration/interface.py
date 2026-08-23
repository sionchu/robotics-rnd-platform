"""Neutral registration contract; no algorithm is selected at bootstrap."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import isfinite

import numpy as np

from robotics_rnd.core.geometry import Transform


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    transform: Transform
    fitness: float
    rmse_m: float

    def __post_init__(self) -> None:
        if not isfinite(self.fitness) or not 0.0 <= self.fitness <= 1.0:
            raise ValueError("registration fitness must be finite and in [0, 1]")
        if not isfinite(self.rmse_m) or self.rmse_m < 0.0:
            raise ValueError("registration RMSE must be a non-negative meter value")


class RegistrationInterface(ABC):
    @abstractmethod
    def register(self, source_points_m: np.ndarray, target_points_m: np.ndarray) -> RegistrationResult:
        raise NotImplementedError
