#!/usr/bin/env python3
"""Generate a generic OpenUSD workcell from a validated JSON/YAML manifest."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

from robotics_rnd.exchange.workcell import WorkcellManifest, load_workcell_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_ROOT / "config/workcells/minimal-workcell.yaml"
DEFAULT_SCHEMA = PROJECT_ROOT / "schemas/workcell-exchange-v1.schema.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports/local/openusd/generic_robot_camera.usda",
    )
    return parser.parse_args()


def generate_stage(manifest: WorkcellManifest, output: Path) -> Path:
    """Write and reopen a metric Z-up USD stage from a validated manifest."""

    from pxr import Gf, Usd, UsdGeom

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(output))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.GetRootLayer().customLayerData = {
        "workcell_id": manifest.workcell_id,
        "workcell_schema_version": "1.0.0",
        "transform_convention": "T_target_source",
    }

    prim_by_path: dict[str, object] = {}
    for spec in sorted(manifest.usd_prims, key=lambda item: (item.path.count("/"), item.path)):
        if spec.prim_type == "Camera":
            schema_prim = UsdGeom.Camera.Define(stage, spec.path)
        else:
            schema_prim = UsdGeom.Xform.Define(stage, spec.path)
        prim = schema_prim.GetPrim()
        prim_by_path[spec.path] = prim
        prim.SetCustomDataByKey("workcell_frame_id", str(spec.frame_id))
        prim.SetCustomDataByKey("workcell_transform_convention", "T_target_source")
        parent_frame = manifest.prim_parent_frame(spec)
        transform = manifest.resolve_transform(parent_frame, spec.frame_id)
        xformable = UsdGeom.Xformable(prim)
        xformable.AddTranslateOp().Set(
            Gf.Vec3d(transform.translation_m.x, transform.translation_m.y, transform.translation_m.z)
        )
        xformable.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(
            Gf.Quatd(
                transform.rotation.w,
                Gf.Vec3d(transform.rotation.x, transform.rotation.y, transform.rotation.z),
            )
        )

    stage.SetDefaultPrim(prim_by_path[manifest.usd_default_prim])
    stage.GetRootLayer().Save()
    reopened = Usd.Stage.Open(str(output))
    if reopened is None or reopened.GetDefaultPrim().GetPath().pathString != manifest.usd_default_prim:
        raise RuntimeError("generated USD stage failed reopen/default-prim validation")
    return output


def main() -> int:
    if importlib.util.find_spec("pxr") is None:
        print("OpenUSD Python package 'pxr' is not available in this interpreter.")
        return 2

    args = parse_args()
    manifest = load_workcell_manifest(args.manifest.resolve(), args.schema.resolve())
    output = generate_stage(manifest, args.output)
    print(f"Created {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
