# Third-Party Provenance

Verified 2026-08-23. This inventory records engineering provenance and is not
legal advice. No external repository, vendor sample, binary, robot data, or KAI
Robotics Vision implementation was copied into this repository.

| Technology | Revision reviewed / runtime | License status | Use decision | Code copied | Boundary |
|---|---|---|---|---|---|
| rbpodo | v0.16.14 / `f6ef41adf629dd27c96b0d3e7ebf3d3fc0cc53c4` | Apache-2.0 | `WRAP_WITH_ADAPTER`; optional, not installed by default | false | `drivers/rainbow/rbpodo_backend.py` |
| rbpodo_ros2 | `5e8294a985e7ce5e20e70564c2681130afc5f502`, unreleased main | `NOASSERTION` aggregate: no root license; package declarations vary | `REFERENCE_ONLY` | false | future optional ROS bridge only |
| RB Cobot docs | online docs / source `bf23897e32e2` | `NOASSERTION`; no repository license detected | `REFERENCE_ONLY`, facts paraphrased | false | research/safety records |
| ROS 2 Jazzy / ros2_control | local ros-base package snapshot and official Jazzy docs | multiple upstream OSS licenses | `REFERENCE_ONLY` for future bridge | false | `integrations/ros2` |
| NumPy | platform dependency `>=1.26,<3` | BSD-3-Clause upstream | `USE_AS_DEPENDENCY` | false | numerical core/mapping |
| OpenCV | runtime 4.14.0, optional `>=4.10,<5` | Apache-2.0 upstream | existing `USE_AS_DEPENDENCY` for vision only | false | `drivers/opencv`, vision extra |

The Rainbow pose conversion is an independent implementation of public unit and
Euler convention facts (`REIMPLEMENT_GENERIC`). The fake backend, lifecycle,
faults, journal, replay, application service, tests, and experiments are
platform-owned. See the registries and `docs/research/TECHNOLOGY_DECISIONS.md`
for URLs, exact evidence, maintenance snapshots, and revisit triggers.
