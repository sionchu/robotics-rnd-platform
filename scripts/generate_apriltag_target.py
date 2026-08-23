#!/usr/bin/env python3
"""Generate a printable SVG AprilTag target with a scale-reference line."""

from __future__ import annotations

import argparse
from pathlib import Path
from xml.sax.saxutils import escape

import cv2
import numpy as np

FAMILIES = {"tag36h11": cv2.aruco.DICT_APRILTAG_36h11}


def marker_modules(family: str, tag_id: int) -> np.ndarray:
    dictionary = cv2.aruco.getPredefinedDictionary(FAMILIES[family])
    modules = dictionary.markerSize + 2
    return np.asarray(cv2.aruco.generateImageMarker(dictionary, tag_id, modules), dtype=np.uint8)


def generate_svg(*, family: str, tag_id: int, nominal_tag_size_mm: float) -> str:
    if family not in FAMILIES:
        raise ValueError(f"unsupported family: {family}")
    if tag_id < 0 or nominal_tag_size_mm <= 0.0:
        raise ValueError("tag id must be non-negative and nominal size must be positive")
    marker = marker_modules(family, tag_id)
    module_size = nominal_tag_size_mm / len(marker)
    tag_x, tag_y = 30.0, 30.0
    rectangles: list[str] = []
    for row, column in zip(*np.where(marker == 0), strict=True):
        rectangles.append(
            f'<rect x="{tag_x + column * module_size:.6f}" '
            f'y="{tag_y + row * module_size:.6f}" width="{module_size:.6f}" '
            f'height="{module_size:.6f}" fill="black"/>'
        )
    label = escape(f"{family} id {tag_id}; nominal outer size {nominal_tag_size_mm:g} mm")
    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">',
            '<rect width="210" height="297" fill="white"/>',
            f'<rect x="{tag_x}" y="{tag_y}" width="{nominal_tag_size_mm}" '
            f'height="{nominal_tag_size_mm}" fill="white" stroke="none"/>',
            *rectangles,
            f'<text x="30" y="{tag_y + nominal_tag_size_mm + 10:.3f}" '
            f'font-family="sans-serif" font-size="4">{label}</text>',
            f'<line x1="30" y1="{tag_y + nominal_tag_size_mm + 22:.3f}" x2="130" '
            f'y2="{tag_y + nominal_tag_size_mm + 22:.3f}" stroke="black" stroke-width="0.5"/>',
            f'<line x1="30" y1="{tag_y + nominal_tag_size_mm + 20:.3f}" x2="30" '
            f'y2="{tag_y + nominal_tag_size_mm + 24:.3f}" stroke="black" stroke-width="0.5"/>',
            f'<line x1="130" y1="{tag_y + nominal_tag_size_mm + 20:.3f}" x2="130" '
            f'y2="{tag_y + nominal_tag_size_mm + 24:.3f}" stroke="black" stroke-width="0.5"/>',
            f'<text x="65" y="{tag_y + nominal_tag_size_mm + 28:.3f}" '
            'font-family="sans-serif" font-size="4">100 mm scale reference</text>',
            f'<text x="30" y="{tag_y + nominal_tag_size_mm + 38:.3f}" '
            'font-family="sans-serif" font-size="4">Print at 100%; disable Fit to Page.</text>',
            f'<text x="30" y="{tag_y + nominal_tag_size_mm + 45:.3f}" '
            'font-family="sans-serif" font-size="4">Measure the printed black outer square; '
            "use the measured value in PnP.</text>",
            "</svg>",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=tuple(FAMILIES), default="tag36h11")
    parser.add_argument("--tag-id", type=int, default=7)
    parser.add_argument("--nominal-tag-size-mm", type=float, default=120.0)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        generate_svg(
            family=arguments.family,
            tag_id=arguments.tag_id,
            nominal_tag_size_mm=arguments.nominal_tag_size_mm,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
