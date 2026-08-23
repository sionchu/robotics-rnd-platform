# ADR 0002 — Audited robot command boundary

Status: Accepted for software validation on 2026-08-23.

## Context

Vendor ACKs, broadcast responses, timeouts, reconnects, units, and fault codes do
not directly satisfy a truthful generic application contract.

## Decision

Keep command IDs, lifecycle, faults, SI units, framed poses, application state,
journals, replay, and reconnect lockout platform-owned. Wrap rbpodo only in an
optional Rainbow backend. Treat acceptance and completion as distinct. Treat an
in-flight connection loss as `UNKNOWN`, never auto-replay/resume, and require
explicit stable-state acknowledgement after reconnect.

## Consequences

Mock/fake/replay implementations share the application surface and generic CI
stays vendor/ROS-free. Live support requires version review and physical gates.
Some vendor functionality remains intentionally unavailable. Software stop is
not safety-rated. The conservative model may require operator resolution where a
controller eventually completed work but evidence is ambiguous.
