# ADR 0002: Vendor-Neutral Workcell Exchange Schema

## Status

Accepted on 2026-08-24.

## Context

Robotics experiments, OpenUSD tools, and a future manufacturing digital-twin
repository need a compact interchange contract. Direct USD authoring alone does
not make units, quaternion order, frame roles, or transform direction explicit,
and coupling the robotics core to OpenUSD would violate the optional-adapter
boundary.

## Decision

Adopt a versioned JSON Schema plus equivalent JSON/YAML manifests. The exchange
package remains outside `robotics_rnd.core`, uses core `FrameId` and `Transform`
for semantic validation, and contains no OpenUSD or simulator imports. OpenUSD
generation remains under `experiments/openusd` and consumes only a validated
manifest.

The v1 constants are metres, radians, normalized XYZW quaternions, right-handed
Z-up coordinates, and `T_target_source` transform direction. The required roles
are world, robot base, tool, camera, fixture, and target.

## Consequences

- JSON Schema and YAML parsing are optional `workcell` dependencies.
- OpenUSD remains a separate optional dependency.
- Consumers can validate transform semantics without OpenUSD, CUDA, ROS, Isaac,
  Docker, Blender, vendor SDKs, or manufacturing simulation code.
- A breaking convention change requires a new schema major version.
