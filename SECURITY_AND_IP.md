# Security and IP Boundaries

## Default posture

This repository is private by default. Nothing is published automatically. A
future public extraction requires a separate review of code, history, data,
licenses, documentation, screenshots, and metadata.

## Never commit

- credentials, API keys, tokens, private keys, `.env` files, or license files;
- company-specific names, processes, recipes, internal protocol details, or UI;
- production robot coordinates, poses, workspaces, or calibration results;
- IP addresses, serial numbers, plant/network topology, or private host details;
- CAD files, CAD-derived geometry, private datasets, captures, bags, videos,
  models, screenshots, or logs;
- vendor SDK binaries, archives, samples, or files without clear redistribution
  rights;
- files or Git history copied from KAI Robotics Vision.

Robot journals are local evidence, not automatically safe artifacts. The
platform redacts address/token/serial-like keys, but free-form vendor/controller
messages still require human review. Keep raw sessions under ignored local
storage and commit only purpose-built sanitized fixtures.

When portability or ownership is ambiguous, leave the item out and classify it
`DO-NOT-MIGRATE` in the private migration inventory.

## Adapter policy

Vendor SDKs are optional adapters. Generic packages do not import `rbpodo`,
Mech-Eye/Mech-Vision SDKs, ROS 2, Raspberry Pi libraries, CUDA APIs, Isaac ROS,
or camera-vendor modules. Adapters expose only platform-owned models.
External inspection clones live under ignored `.external/` or `/tmp`; intake
never authorizes executing third-party scripts or copying source.

## Before every commit

1. Inspect `git status --short`.
2. Inspect `git diff --cached --name-only` and the staged diff.
3. Run relevant tests and `git diff --check`.
4. Scan staged text for credentials, tokens, private addresses, serials, and KAI
   operational terms.
5. Review tracked file types and sizes for binaries, captures, datasets, models,
   logs, and vendor packages.

Before a remote is created or pushed, verify that it is private and that the
authenticated account is intended for this repository. Never force-push or
rewrite the KAI repository.

## Data and model handling

Tracked `datasets/` and `models/` content is documentation only. Raw/processed
data, trained/pretrained weights, ROS bags, point clouds, captures, and videos
remain ignored. Introduce DVC or Git LFS only after a real reviewed need exists.

## Incident response

If sensitive material is staged, unstage it without deleting the local source,
add a precise ignore rule, and document the finding. If it was committed or
pushed, stop distribution work and obtain owner/security guidance before any
history rewrite.
