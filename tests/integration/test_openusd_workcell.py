from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pxr")

from pxr import Usd, UsdGeom

from experiments.openusd.create_stage import generate_stage
from robotics_rnd.exchange import load_workcell_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "schemas/workcell-exchange-v1.schema.json"
MANIFEST_PATH = PROJECT_ROOT / "config/workcells/minimal-workcell.yaml"


def test_manifest_generates_reopenable_metric_workcell_stage(tmp_path: Path) -> None:
    manifest = load_workcell_manifest(MANIFEST_PATH, SCHEMA_PATH)
    output = generate_stage(manifest, tmp_path / "minimal-workcell.usda")

    stage = Usd.Stage.Open(str(output))
    assert stage is not None
    assert stage.GetDefaultPrim().GetPath().pathString == "/World"
    assert UsdGeom.GetStageMetersPerUnit(stage) == pytest.approx(1.0)
    assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z
    assert {prim.GetPath().pathString for prim in stage.Traverse()} == {
        "/World",
        "/Robot",
        "/Robot/Tool",
        "/Camera",
        "/Fixture",
        "/Target",
    }
    assert stage.GetPrimAtPath("/Camera").IsA(UsdGeom.Camera)
    assert stage.GetRootLayer().customLayerData["transform_convention"] == "T_target_source"

    for prim_spec in manifest.usd_prims:
        prim = stage.GetPrimAtPath(prim_spec.path)
        assert prim.GetCustomDataByKey("workcell_frame_id") == str(prim_spec.frame_id)
        expected = manifest.resolve_transform(manifest.prim_parent_frame(prim_spec), prim_spec.frame_id)
        translation = prim.GetAttribute("xformOp:translate").Get()
        orientation = prim.GetAttribute("xformOp:orient").Get()
        imaginary = orientation.GetImaginary()
        assert list(translation) == pytest.approx(expected.translation_m.as_array())
        assert [imaginary[0], imaginary[1], imaginary[2], orientation.GetReal()] == pytest.approx(
            [
                expected.rotation.x,
                expected.rotation.y,
                expected.rotation.z,
                expected.rotation.w,
            ]
        )
