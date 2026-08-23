"""Reprojection metrics with explicit pixel units."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class ReprojectionMetrics:
    rms_px: float
    mean_px: float
    max_px: float
    per_view_rms_px: tuple[float, ...]

    def __post_init__(self) -> None:
        scalars = (self.rms_px, self.mean_px, self.max_px, *self.per_view_rms_px)
        if not self.per_view_rms_px or not all(isfinite(value) and value >= 0.0 for value in scalars):
            raise ValueError("reprojection metrics must be finite non-negative pixels")


def reprojection_metrics(
    observed_views_px: tuple[NDArray[np.float64], ...],
    projected_views_px: tuple[NDArray[np.float64], ...],
    solver_rms_px: float,
) -> ReprojectionMetrics:
    if not observed_views_px or len(observed_views_px) != len(projected_views_px):
        raise ValueError("observed and projected view counts must match and be non-empty")
    all_errors: list[NDArray[np.float64]] = []
    per_view: list[float] = []
    for observed, projected in zip(observed_views_px, projected_views_px, strict=True):
        observed_array = np.asarray(observed, dtype=np.float64)
        projected_array = np.asarray(projected, dtype=np.float64)
        if observed_array.shape != projected_array.shape or observed_array.ndim != 2:
            raise ValueError("observed and projected point shapes must match")
        errors = np.linalg.norm(observed_array - projected_array, axis=1)
        all_errors.append(errors)
        per_view.append(float(np.sqrt(np.mean(np.square(errors)))))
    combined = np.concatenate(all_errors)
    return ReprojectionMetrics(
        rms_px=float(solver_rms_px),
        mean_px=float(np.mean(combined)),
        max_px=float(np.max(combined)),
        per_view_rms_px=tuple(per_view),
    )
