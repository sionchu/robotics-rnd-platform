from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_ROOTS = {
    "cv2",
    "RPi",
    "Jetson",
    "carb",
    "cuda",
    "isaac_ros",
    "isaacsim",
    "mecheye",
    "omni",
    "pxr",
    "pycuda",
    "pythoncom",
    "rbpodo",
    "rclpy",
    "rospy",
    "torch",
    "win32api",
    "win32con",
    "zivid",
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
        if "import rbpodo" in text or "from mecheye" in text:
            violations.append(str(path))
    assert violations == []


def test_exchange_layer_does_not_import_runtime_adapters() -> None:
    exchange_root = Path("src/robotics_rnd/exchange")
    forbidden = FORBIDDEN_ROOTS | {"docker", "omni", "isaacsim"}
    violations: list[str] = []
    for path in exchange_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import | ast.ImportFrom) and imported_root(node) in forbidden:
                violations.append(f"{path}:{node.lineno}:{imported_root(node)}")
    assert violations == []


def test_openusd_generator_has_no_simulation_or_vendor_imports() -> None:
    path = Path("experiments/openusd/create_stage.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden = {"carb", "cuda", "isaacsim", "omni", "rbpodo", "rclpy", "torch"}
    violations = [
        f"{path}:{node.lineno}:{imported_root(node)}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom) and imported_root(node) in forbidden
    ]
    assert violations == []
