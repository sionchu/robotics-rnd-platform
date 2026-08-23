# Technology Decisions

Verified on 2026-08-23. Status vocabulary is defined by
`EXTERNAL_RESEARCH_INTAKE.md`.

## rbpodo — WRAP_WITH_ADAPTER

**Problem:** Direct RB-series control needs official command, response, state,
and IO access without leaking vendor objects or units.

**Candidates:** direct socket reimplementation, direct `rbpodo`, optional
`rbpodo` adapter, official ROS 2 package.

**Evidence:** Official repository `f6ef41adf629` and release `0.16.14`; official
README/docs/source/examples/changelog; selected public issues and PR 6.

**License:** Apache-2.0 verified from the repository license.

**Maintenance/API stability:** Active releases through 2026-07-23, but the
README explicitly states the API is under development and subject to change.

**Performance evidence:** No live controller or network benchmark. Mock metrics
are `SOFTWARE_ONLY`.

**Platform coupling:** High if imported directly; bounded when isolated under
`drivers/rainbow` with platform-owned DTOs and feature detection.

**Decision:** `WRAP_WITH_ADAPTER`. `rbpodo` remains an optional, separately
installed dependency. v0.3 reviews 0.16.14 and fails clearly for unsupported
versions/surfaces.

**Reason:** The official library already represents the controller protocol and
provides Python/C++ bindings, while its response buffering, evolving API, and
vendor units require a strict compatibility layer.

**Revisit trigger:** A new reviewed rbpodo version, controller firmware evidence,
or LEVEL 1 read-only validation.

## rbpodo_ros2 — REFERENCE_ONLY

**Problem:** Determine whether ROS 2 should be the platform's direct RB control
layer.

**Candidates:** official `rbpodo_ros2`, platform core plus optional future ROS
bridge, direct `rbpodo` adapter.

**Evidence:** Official repository commit `5e8294a985e7`; README, package manifests,
messages/actions, ros2_control hardware code, launch files, and public issues.

**License:** Root repository license is absent and GitHub reports no detected
license. Individual manifests mostly declare Apache-2.0; MoveIt configuration
declares BSD-3-Clause. Aggregate redistribution status is therefore recorded as
`NOASSERTION` pending clarification.

**Maintenance/API stability:** Active in 2026 but no releases/tags; README says
active development and not for production. Installation explicitly targets ROS
2 Humble, while this platform's optional ROS baseline is Jazzy.

**Performance evidence:** No platform benchmark and no live hardware.

**Platform coupling:** Pulls ros2_control, MoveIt, messages, URDF, RViz, and ROS
lifecycle into the deployment path.

**Decision:** `REFERENCE_ONLY`. Learn from its read/write separation, resource
locking, SI conversions, state message, and MoveIt path; do not depend on it.

**Reason:** ROS tooling is valuable for future planning and visualization, but
it is not required for a hardware-independent application service or direct
adapter and currently conflicts with the platform's Jazzy/optional boundary.

**Revisit trigger:** A supported Jazzy release with explicit aggregate license,
hardware evidence, or a concrete MoveIt/ros2_control application requirement.

## Rainbow official documentation — REFERENCE_ONLY

**Problem:** Establish authoritative ports, state/IO layout, coordinate systems,
script semantics, and safety context.

**Evidence:** Official online RB Cobot docs and repository commit `bf23897e32e2`,
including External Script Control API, UI Script v6.10, reqdata v6.10, coordinate,
IO, setup, and safety pages.

**License:** No repository license detected; no content is copied. Facts are
paraphrased and linked.

**Decision:** `REFERENCE_ONLY` and use as the primary semantic source for the
adapter and handoff.

**Revisit trigger:** Controller/document version supplied by actual LEVEL 1
hardware evidence.

## OpenCV — USE_AS_DEPENDENCY

Existing decision retained: optional `vision` extra, reviewed runtime 4.14.0,
bounded to major version 4, Apache-2.0. It does not enter robot control.

## ROS 2 Jazzy / ros2_control — REFERENCE_ONLY

The host's optional Jazzy installation informs future message and lifecycle
mapping. Generic core and CI remain ROS-free. Official ros2_control architecture
supports the same conceptual separation—resource-managed hardware interfaces
with read/write lifecycle—but no ROS bridge is implemented in v0.3.
