from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from robotics_rnd.core import FrameId
from robotics_rnd.exchange import (
    dump_workcell_json,
    load_workcell_manifest,
    parse_workcell_manifest,
    validate_document,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "schemas/workcell-exchange-v1.schema.json"
JSON_MANIFEST = PROJECT_ROOT / "config/workcells/minimal-workcell.json"
YAML_MANIFEST = PROJECT_ROOT / "config/workcells/minimal-workcell.yaml"


def read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_json_schema_and_yaml_define_the_same_canonical_workcell() -> None:
    schema = read_json(SCHEMA_PATH)
    document = read_json(JSON_MANIFEST)
    validate_document(document, schema)

    json_workcell = load_workcell_manifest(JSON_MANIFEST, SCHEMA_PATH)
    yaml_workcell = load_workcell_manifest(YAML_MANIFEST, SCHEMA_PATH)
    assert json_workcell == yaml_workcell
    assert {frame.role for frame in json_workcell.frames} == {
        "world",
        "robot_base",
        "tool",
        "camera",
        "fixture",
        "target",
    }
    assert {prim.path for prim in json_workcell.usd_prims} >= {
        "/World",
        "/Robot",
        "/Camera",
        "/Fixture",
        "/Target",
    }


def test_manifest_json_round_trip_preserves_frames_and_transforms(tmp_path: Path) -> None:
    original = load_workcell_manifest(YAML_MANIFEST, SCHEMA_PATH)
    output = tmp_path / "round-trip.json"
    dump_workcell_json(original, output)
    restored = load_workcell_manifest(output, SCHEMA_PATH)
    assert restored == original


def test_transform_tree_uses_core_target_source_composition() -> None:
    workcell = load_workcell_manifest(JSON_MANIFEST, SCHEMA_PATH)
    world = workcell.frame_for_role("world")
    tool = workcell.frame_for_role("tool")
    target = workcell.frame_for_role("target")

    t_world_tool = workcell.resolve_transform(world, tool)
    t_world_target = workcell.resolve_transform(world, target)
    assert t_world_tool.name == "T_world_tool"
    assert np.allclose(t_world_tool.translation_m.as_array(), [0.0, 0.0, 0.45])
    assert np.allclose(t_world_target.translation_m.as_array(), [0.8, 0.0, 0.1])
    assert np.allclose((t_world_target @ t_world_target.inverse()).as_matrix(), np.eye(4), atol=1.0e-12)


def test_schema_and_semantic_validation_reject_ambiguous_units_and_transforms() -> None:
    schema = read_json(SCHEMA_PATH)
    wrong_units = read_json(JSON_MANIFEST)
    conventions = wrong_units["conventions"]
    assert isinstance(conventions, dict)
    conventions["length_unit"] = "millimetre"
    with pytest.raises(ValueError, match="schema validation failed"):
        validate_document(wrong_units, schema)

    non_normalized = copy.deepcopy(read_json(JSON_MANIFEST))
    transforms = non_normalized["transforms"]
    assert isinstance(transforms, list)
    first = transforms[0]
    assert isinstance(first, dict)
    first["rotation_xyzw"] = [0.0, 0.0, 0.0, 2.0]
    with pytest.raises(ValueError, match="must be normalized"):
        parse_workcell_manifest(non_normalized)

    disconnected = copy.deepcopy(read_json(JSON_MANIFEST))
    disconnected_frames = disconnected["frames"]
    assert isinstance(disconnected_frames, list)
    target_frame = disconnected_frames[-1]
    assert isinstance(target_frame, dict)
    target_frame["parent"] = "camera"
    with pytest.raises(ValueError, match="exactly one T_parent_child"):
        parse_workcell_manifest(disconnected)

    with pytest.raises(ValueError, match="unknown transform frame"):
        load_workcell_manifest(JSON_MANIFEST, SCHEMA_PATH).resolve_transform(
            FrameId("world"), FrameId("missing")
        )
