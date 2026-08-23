# Workcell Exchange Schema 1.0

## Purpose

The Workcell Exchange Schema is a small, vendor-neutral contract for exchanging
workcell frame identity, rigid transforms, and OpenUSD prim mappings. It is not a
manufacturing-process model, robot program, CAD container, simulator state, or
vendor SDK serialization.

The normative JSON Schema is `schemas/workcell-exchange-v1.schema.json`.
Equivalent JSON and YAML examples live under `config/workcells/` and are kept in
lockstep by tests.

## Normative conventions

- Length and translation: metres (`metre`, serialized as `translation_m`).
- Angles outside quaternions: radians (`radian`).
- Quaternion order: normalized `(x, y, z, w)` (`rotation_xyzw`).
- Cartesian convention: right-handed, Z-up world.
- Transform name and direction: `T_target_source` maps coordinates expressed in
  `source` into `target`.
- Every non-world frame has exactly one parent and exactly one
  `T_parent_child` edge. The graph must be connected and acyclic.
- Adapters convert vendor, UI, ROS, CAD, or simulator conventions at their
  boundaries. They must not relabel an unconverted transform.

For example, `T_world_camera` maps a camera-frame point into world coordinates,
and `T_world_target = T_world_fixture @ T_fixture_target`.

## Required frame roles

| Role | Origin and axes |
|---|---|
| `world` | Stable workcell reference. +Z is up; +X and +Y are documented by the producer and complete a right-handed frame. It has no parent. |
| `robot_base` | Robot mounting/base reference. The exchange convention uses +X nominally forward, +Y left, and +Z away from the mounting plane. A robot adapter performs any vendor-frame conversion. |
| `tool` | Tool-centre-point reference. +Z is the documented tool approach direction; +X is the selected tool-right direction and +Y completes the right-handed frame. The parent is normally `robot_base`. |
| `camera` | Optical camera reference: +X image-right, +Y image-down, +Z optical-forward. A camera adapter converts SDK-specific camera frames before export. |
| `fixture` | Stable fixture reference selected by the producer. Its axis meaning must be fixed for a schema version and calibration record. |
| `target` | Target-face reference: +X right, +Y up, +Z outward from the observed face. The parent is normally `fixture` or `camera`, depending on whether the value is nominal or observed. |

Frame IDs are portable identifiers and are distinct from roles. The minimal
example uses `world`, `robot_base`, `tool`, `camera`, `fixture`, and `target`, but
consumers should select frames by role rather than assuming those IDs.

## Validation layers

1. JSON Schema validates required fields, constants, types, array sizes, and USD
   path syntax.
2. `robotics_rnd.exchange.workcell` validates unique roles/IDs, normalized XYZW
   quaternions, transform names, tree edges, connectivity, and required USD
   mappings.
3. `robotics_rnd.core.geometry.Transform` composes and inverts the graph, so the
   exchange layer uses the same `T_target_source` behavior as the robotics core.
4. The OpenUSD adapter generates a stage, saves it, and reopens it before
   reporting success.

## Minimal OpenUSD mapping

The example declares these required prim paths:

```text
/World
/Robot
/Camera
/Fixture
/Target
```

It also declares `/Robot/Tool` to retain the required tool frame. The stage is
metric and Z-up. Each prim records its workcell frame ID and transform convention
as platform-owned metadata. Camera is an OpenUSD `Camera`; other prims are empty
`Xform` nodes. No geometry, CAD, material, physics, process, or simulator feature
is implied.

## Compatibility and change control

- Producers emit `schema_version: 1.0.0` and preserve the exact convention
  constants.
- Consumers reject unknown major versions and invalid graphs rather than
  guessing units or transform direction.
- Optional future fields require a reviewed schema revision. A breaking unit,
  frame, or transform semantic requires a new major version.
- Asset bytes, calibration captures, production poses, and generated USD remain
  governed by `docs/data/DATA_POLICY.md` and are not embedded in this manifest.
