"""Vendor-independent fiducial detection models and implementations."""

from .apriltag import OpenCvAprilTagDetector
from .models import AprilTagObservation

__all__ = ["AprilTagObservation", "OpenCvAprilTagDetector"]
