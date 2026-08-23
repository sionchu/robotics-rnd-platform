# RB Hardware Validation Levels

Current highest completed level: **LEVEL 0**.

## LEVEL 0 — No hardware

Official/public research, source inspection, mock/fake contracts, deterministic
fault injection, journal/replay, and application demos. No controller connection
or physical behavior claim.

## LEVEL 1 — Read-only connection

With explicit authorization: identify controller/model/software, record sanitized
versions, verify a reviewed network path, connect in `READ_ONLY`, read state and
IO, verify liveness/timestamps, and disconnect. Motion, IO/config writes, program
execution, activation, and safety changes remain rejected.

## LEVEL 2 — Non-motion write validation

Only under a future approved procedure after LEVEL 1: one reviewed non-motion IO
write with verified wiring/load and restoration. No motion.

## LEVEL 3 — Bounded motion lab

Only with trained operator, risk assessment, clear workspace, known payload/TCP,
controller safety active, emergency-stop access, low limits, explicit command and
stop procedure, independent observer, and recorded evidence.

## LEVEL 4 — Application process integration

Only after prior levels pass: integrate workflow, vision, tooling, recovery,
operator HMI, and application-specific acceptance evidence.

Application software is not a certified safety system. A software stop is not an
emergency stop and mock evidence does not characterize physical performance.
