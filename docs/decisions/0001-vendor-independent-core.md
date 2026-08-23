# ADR 0001: Vendor-independent core with adapter boundaries

- Status: accepted
- Date: 2026-08-23

## Context

The platform must support direct robot/camera APIs, ROS 2, simulation, replay,
edge targets, and future vendors. The inspected vision application demonstrates
the value of interfaces and deterministic replay, but also shows how quickly UI,
protocol, capture formats, and SDK types can become application-specific.

## Decision

Core geometry, models, state transitions, robot contracts, vision contracts, and
skills use platform-owned types with SI units. Vendor SDKs and communication
frameworks live in drivers or integrations and are optional. Applications are
the only composition roots.

## Consequences

- Generic unit, contract, and architecture tests run on a standard CPU host.
- Each adapter must translate units, frames, errors, and capabilities explicitly.
- Some vendor conveniences are deliberately not exposed until a neutral contract
  is justified by more than one use case.
- Hardware validation remains adapter-specific and is never inferred from mocks.
