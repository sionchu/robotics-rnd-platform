from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_ROOTS = {
    "cv2",
    "rbpodo",
    "mecheye",
    "rclpy",
    "rospy",
    "RPi",
    "libcamera",
    "picamera2",
    "rpicam",
    "Jetson",
    "cuda",
    "pycuda",
    "isaac_ros",
    "torch",
}


def imported_root(node: ast.Import | ast.ImportFrom) -> str:
    if isinstance(node, ast.Import):
        return node.names[0].name.split(".")[0]
    return "" if node.module is None else node.module.split(".")[0]


def test_core_has_no_vendor_framework_or_gpu_imports() -> None:
    core = Path("src/robotics_rnd/core")
    violations: list[str] = []
    for path in core.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import | ast.ImportFrom) and imported_root(node) in FORBIDDEN_ROOTS:
                violations.append(f"{path}:{node.lineno}:{imported_root(node)}")
    assert violations == []


def test_vendor_import_names_are_confined_to_driver_tree() -> None:
    source_root = Path("src/robotics_rnd")
    violations: list[str] = []
    for path in source_root.rglob("*.py"):
        if "drivers" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if any(
            marker in text
            for marker in (
                "import rbpodo",
                "from mecheye",
                "import picamera2",
                "from picamera2",
                "import libcamera",
                "from libcamera",
            )
        ):
            violations.append(str(path))
    assert violations == []
