"""Workcell Exchange Schema models and transform-graph validation."""

from __future__ import annotations

import importlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Quaternion, Transform, Vector3

SCHEMA_VERSION = "1.0.0"
SCHEMA_ID = "urn:robotics-rnd:workcell-exchange:1.0.0"
REQUIRED_ROLES = frozenset({"world", "robot_base", "tool", "camera", "fixture", "target"})
REQUIRED_USD_PATH_ROLES = {
    "/World": "world",
    "/Robot": "robot_base",
    "/Camera": "camera",
    "/Fixture": "fixture",
    "/Target": "target",
}
_USD_PATH_PATTERN = re.compile(r"^/[A-Za-z][A-Za-z0-9_]*(?:/[A-Za-z][A-Za-z0-9_]*)*$")


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _sequence(value: object, label: str, length: int | None = None) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    if length is not None and len(value) != length:
        raise ValueError(f"{label} must contain exactly {length} values")
    return value


def _number(value: object, label: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{label} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class FrameSpec:
    """A named workcell frame and its parent in the transform tree."""

    frame_id: FrameId
    role: str
    parent: FrameId | None

    @classmethod
    def from_mapping(cls, value: object) -> FrameSpec:
        item = _mapping(value, "frame")
        parent_value = item.get("parent")
        return cls(
            frame_id=FrameId(_string(item.get("id"), "frame.id")),
            role=_string(item.get("role"), "frame.role"),
            parent=None if parent_value is None else FrameId(_string(parent_value, "frame.parent")),
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "id": str(self.frame_id),
            "role": self.role,
            "parent": None if self.parent is None else str(self.parent),
        }


@dataclass(frozen=True, slots=True)
class TransformSpec:
    """A serialized rigid transform backed by the platform core model."""

    transform: Transform

    @classmethod
    def from_mapping(cls, value: object) -> TransformSpec:
        item = _mapping(value, "transform")
        target = FrameId(_string(item.get("target_frame"), "transform.target_frame"))
        source = FrameId(_string(item.get("source_frame"), "transform.source_frame"))
        translation_values = _sequence(item.get("translation_m"), "transform.translation_m", 3)
        quaternion_values = _sequence(item.get("rotation_xyzw"), "transform.rotation_xyzw", 4)
        quaternion_floats = tuple(
            _number(component, "transform.rotation_xyzw") for component in quaternion_values
        )
        norm = math.sqrt(sum(component * component for component in quaternion_floats))
        if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1.0e-9):
            raise ValueError("transform.rotation_xyzw must be normalized")
        transform = Transform(
            target_frame=target,
            source_frame=source,
            translation_m=Vector3.from_iterable(
                _number(component, "transform.translation_m") for component in translation_values
            ),
            rotation=Quaternion(*quaternion_floats),
        )
        name = _string(item.get("name"), "transform.name")
        if name != transform.name:
            raise ValueError(f"transform.name must be {transform.name}")
        return cls(transform)

    def to_mapping(self) -> dict[str, object]:
        transform = self.transform
        return {
            "name": transform.name,
            "target_frame": str(transform.target_frame),
            "source_frame": str(transform.source_frame),
            "translation_m": [
                transform.translation_m.x,
                transform.translation_m.y,
                transform.translation_m.z,
            ],
            "rotation_xyzw": [
                transform.rotation.x,
                transform.rotation.y,
                transform.rotation.z,
                transform.rotation.w,
            ],
        }


@dataclass(frozen=True, slots=True)
class UsdPrimSpec:
    """A manifest-owned mapping from a USD prim to a workcell frame."""

    path: str
    prim_type: str
    frame_id: FrameId

    @classmethod
    def from_mapping(cls, value: object) -> UsdPrimSpec:
        item = _mapping(value, "usd.prim")
        path = _string(item.get("path"), "usd.prim.path")
        if not _USD_PATH_PATTERN.fullmatch(path):
            raise ValueError(f"invalid absolute USD prim path: {path}")
        return cls(
            path=path,
            prim_type=_string(item.get("type"), "usd.prim.type"),
            frame_id=FrameId(_string(item.get("frame"), "usd.prim.frame")),
        )

    def to_mapping(self) -> dict[str, object]:
        return {"path": self.path, "type": self.prim_type, "frame": str(self.frame_id)}


@dataclass(frozen=True, slots=True)
class WorkcellManifest:
    """Validated, connected workcell transform tree and USD frame mapping."""

    workcell_id: str
    frames: tuple[FrameSpec, ...]
    transforms: tuple[TransformSpec, ...]
    usd_default_prim: str
    usd_prims: tuple[UsdPrimSpec, ...]

    def __post_init__(self) -> None:
        frame_by_id = {frame.frame_id: frame for frame in self.frames}
        if len(frame_by_id) != len(self.frames):
            raise ValueError("frame ids must be unique")

        frame_by_role = {frame.role: frame for frame in self.frames}
        if len(frame_by_role) != len(self.frames):
            raise ValueError("frame roles must be unique")
        missing_roles = REQUIRED_ROLES - frame_by_role.keys()
        if missing_roles:
            raise ValueError(f"missing required frame roles: {', '.join(sorted(missing_roles))}")

        world = frame_by_role["world"]
        if world.parent is not None:
            raise ValueError("world frame must not have a parent")
        for frame in self.frames:
            if frame == world:
                continue
            if frame.parent is None or frame.parent not in frame_by_id:
                raise ValueError(f"frame {frame.frame_id} must reference an existing parent")

        transform_by_edge = {
            (item.transform.target_frame, item.transform.source_frame): item.transform
            for item in self.transforms
        }
        if len(transform_by_edge) != len(self.transforms):
            raise ValueError("transform edges must be unique")
        expected_edges = {(frame.parent, frame.frame_id) for frame in self.frames if frame.parent is not None}
        if set(transform_by_edge) != expected_edges:
            raise ValueError("transforms must contain exactly one T_parent_child edge per non-world frame")

        self.world_transforms()

        prim_by_path = {prim.path: prim for prim in self.usd_prims}
        if len(prim_by_path) != len(self.usd_prims):
            raise ValueError("USD prim paths must be unique")
        if self.usd_default_prim != "/World":
            raise ValueError("usd.default_prim must be /World")
        if self.usd_default_prim not in prim_by_path:
            raise ValueError("usd.default_prim must reference a declared prim")
        for prim in self.usd_prims:
            if prim.frame_id not in frame_by_id:
                raise ValueError(f"USD prim {prim.path} references unknown frame {prim.frame_id}")
        for path, role in REQUIRED_USD_PATH_ROLES.items():
            if path not in prim_by_path:
                raise ValueError(f"missing required USD prim path: {path}")
            if prim_by_path[path].frame_id != frame_by_role[role].frame_id:
                raise ValueError(f"USD prim {path} must map to the {role} frame")

    @property
    def world_frame(self) -> FrameId:
        return next(frame.frame_id for frame in self.frames if frame.role == "world")

    def frame_for_role(self, role: str) -> FrameId:
        try:
            return next(frame.frame_id for frame in self.frames if frame.role == role)
        except StopIteration as exc:
            raise ValueError(f"unknown frame role: {role}") from exc

    def world_transforms(self) -> dict[FrameId, Transform]:
        """Resolve every `T_world_frame` through core transform composition."""

        frame_by_id = {frame.frame_id: frame for frame in self.frames}
        edge_by_source = {item.transform.source_frame: item.transform for item in self.transforms}
        world = next(frame.frame_id for frame in self.frames if frame.role == "world")
        resolved: dict[FrameId, Transform] = {world: Transform.identity(world)}
        visiting: set[FrameId] = set()

        def resolve(frame_id: FrameId) -> Transform:
            if frame_id in resolved:
                return resolved[frame_id]
            if frame_id in visiting:
                raise ValueError("frame graph contains a cycle")
            visiting.add(frame_id)
            frame = frame_by_id[frame_id]
            if frame.parent is None:
                raise ValueError(f"frame {frame_id} is disconnected from world")
            parent_transform = resolve(frame.parent)
            world_transform = parent_transform @ edge_by_source[frame_id]
            visiting.remove(frame_id)
            resolved[frame_id] = world_transform
            return world_transform

        for frame_id in frame_by_id:
            resolve(frame_id)
        return resolved

    def resolve_transform(self, target_frame: FrameId, source_frame: FrameId) -> Transform:
        """Resolve `T_target_source` using the validated world transform tree."""

        world_transforms = self.world_transforms()
        try:
            target_from_world = world_transforms[target_frame].inverse()
            world_from_source = world_transforms[source_frame]
        except KeyError as exc:
            raise ValueError(f"unknown transform frame: {exc.args[0]}") from exc
        return target_from_world @ world_from_source

    def prim_parent_frame(self, prim: UsdPrimSpec) -> FrameId:
        parent_path = prim.path.rsplit("/", maxsplit=1)[0]
        if parent_path:
            parent = next((candidate for candidate in self.usd_prims if candidate.path == parent_path), None)
            if parent is not None:
                return parent.frame_id
        return self.world_frame

    def to_mapping(self) -> dict[str, object]:
        return {
            "$schema": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "workcell_id": self.workcell_id,
            "conventions": {
                "length_unit": "metre",
                "angle_unit": "radian",
                "quaternion_order": "xyzw",
                "transform_convention": "T_target_source",
                "handedness": "right-handed",
                "up_axis": "Z",
            },
            "frames": [frame.to_mapping() for frame in self.frames],
            "transforms": [transform.to_mapping() for transform in self.transforms],
            "usd": {
                "default_prim": self.usd_default_prim,
                "prims": [prim.to_mapping() for prim in self.usd_prims],
            },
        }


def validate_document(document: Mapping[str, object], schema: Mapping[str, object]) -> None:
    """Validate a raw manifest against the published JSON Schema."""

    try:
        validators = importlib.import_module("jsonschema.validators")
    except ModuleNotFoundError as exc:
        raise RuntimeError("JSON Schema validation requires the 'workcell' optional dependency") from exc
    validator_type = validators.validator_for(schema)
    validator_type.check_schema(schema)
    errors = sorted(validator_type(schema).iter_errors(document), key=lambda error: list(error.absolute_path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "document"
        raise ValueError(f"schema validation failed at {location}: {error.message}")


def parse_workcell_manifest(document: Mapping[str, object]) -> WorkcellManifest:
    """Parse a schema-shaped mapping and enforce semantic graph invariants."""

    if document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    if document.get("$schema") != SCHEMA_ID:
        raise ValueError(f"$schema must be {SCHEMA_ID}")
    conventions = _mapping(document.get("conventions"), "conventions")
    expected_conventions = {
        "length_unit": "metre",
        "angle_unit": "radian",
        "quaternion_order": "xyzw",
        "transform_convention": "T_target_source",
        "handedness": "right-handed",
        "up_axis": "Z",
    }
    if dict(conventions) != expected_conventions:
        raise ValueError("manifest conventions do not match Workcell Exchange Schema 1.0.0")

    frames = tuple(FrameSpec.from_mapping(item) for item in _sequence(document.get("frames"), "frames"))
    transforms = tuple(
        TransformSpec.from_mapping(item) for item in _sequence(document.get("transforms"), "transforms")
    )
    usd = _mapping(document.get("usd"), "usd")
    prims = tuple(UsdPrimSpec.from_mapping(item) for item in _sequence(usd.get("prims"), "usd.prims"))
    return WorkcellManifest(
        workcell_id=_string(document.get("workcell_id"), "workcell_id"),
        frames=frames,
        transforms=transforms,
        usd_default_prim=_string(usd.get("default_prim"), "usd.default_prim"),
        usd_prims=prims,
    )


def _load_document(path: Path) -> Mapping[str, object]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        value = json.loads(text)
    elif path.suffix.lower() in {".yaml", ".yml"}:
        try:
            yaml = importlib.import_module("yaml")
        except ModuleNotFoundError as exc:
            raise RuntimeError("YAML loading requires the 'workcell' optional dependency") from exc
        value = yaml.safe_load(text)
    else:
        raise ValueError("workcell manifest must use .json, .yaml, or .yml")
    return _mapping(value, "manifest")


def load_workcell_manifest(path: Path, schema_path: Path | None = None) -> WorkcellManifest:
    """Load JSON/YAML, optionally validate JSON Schema, then validate semantics."""

    document = _load_document(path)
    if schema_path is not None:
        schema = _mapping(json.loads(schema_path.read_text(encoding="utf-8")), "schema")
        validate_document(document, schema)
    return parse_workcell_manifest(document)


def dump_workcell_json(manifest: WorkcellManifest, path: Path) -> None:
    """Write a deterministic JSON representation for exchange or review."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(manifest.to_mapping(), indent=2)}\n", encoding="utf-8")
