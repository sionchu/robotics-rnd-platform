#!/usr/bin/env python3
"""Create a small generic robot/camera OpenUSD stage without Isaac dependencies."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports/local/openusd/generic_robot_camera.usda",
    )
    return parser.parse_args()


def main() -> int:
    if importlib.util.find_spec("pxr") is None:
        print("OpenUSD Python package 'pxr' is not available in this interpreter.")
        return 2

    from pxr import Gf, Usd, UsdGeom

    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    stage = Usd.Stage.CreateNew(str(args.output.resolve()))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    robot = UsdGeom.Xform.Define(stage, "/World/Robot")
    robot.GetPrim().SetCustomDataByKey("asset_role", "generic_robot")
    base = UsdGeom.Cube.Define(stage, "/World/Robot/Base")
    base.GetSizeAttr().Set(0.4)
    UsdGeom.XformCommonAPI(base).SetScale(Gf.Vec3f(1.0, 0.75, 0.25))

    camera_rig = UsdGeom.Xform.Define(stage, "/World/CameraRig")
    UsdGeom.XformCommonAPI(camera_rig).SetTranslate(Gf.Vec3d(1.0, -1.0, 1.2))
    camera = UsdGeom.Camera.Define(stage, "/World/CameraRig/Camera")
    camera.GetFocalLengthAttr().Set(24.0)
    camera.GetClippingRangeAttr().Set(Gf.Vec2f(0.05, 100.0))

    stage.GetRootLayer().Save()
    print(f"Created {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
