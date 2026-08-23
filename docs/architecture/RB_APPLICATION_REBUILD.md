# RB Application Rebuild Boundary

## Decision

A future RB application is rebuilt around platform contracts; no KAI Robotics
Vision source, history, GUI, job recipe, controller address, or operational data
is migrated. The generic platform remains the reusable dependency and KRV remains
an external repository/consumer.

## Layers

| Layer | Owns | Must not own |
|---|---|---|
| HMI | user intent, display, explicit confirmation | rbpodo objects, raw sockets, completion inference |
| Application service | session IDs, state projection, journal, command submission | vendor units, GUI widgets, safety certification |
| Generic robot | capability, command/state/result/fault/lifecycle contracts | Rainbow/ROS terminology |
| Rainbow adapter | version/features, SI conversion, response/fault mapping | jobs, recipes, plant details |
| Backend | optional vendor calls or deterministic fake | application state |
| Replay | portable recorded platform results | vendor binary formats |

## HMI state projection

The application consumes `DISCONNECTED`, `READY`, `BUSY`, `PAUSED`, `STOPPED`,
`DEGRADED`, and `FAULTED`. Vendor codes remain diagnostics. A `DEGRADED` state or
`UNKNOWN` command disables motion intent until the application presents the
uncertainty and an authorized reviewer completes resynchronization.

## ROS 2 boundary

The official `rbpodo_ros2` project informs lifecycle, resource, state, MoveIt,
and ros2_control research, but v0.3 does not depend on it. A future Jazzy bridge
maps platform DTOs at an integration boundary; it does not replace the generic
application service or become a core import.

## Vision and future integration

Vision supplies a framed, quality-gated platform pose. Future Mech-Mind
composition selects `MechEyeDriver` for acquisition or `MechVisionProvider` for
external results behind `VisionInterface`; neither SDK enters robot/HMI models.
A future job must validate `T_base_camera`, target quality, workspace bounds, and
physical uncertainty before forming a robot command. v0.3 does not connect vision
to live motion.

## Acceptance before rebuilding an application

Use a tagged platform release; keep local configuration untracked; pass mock and
replay workflows; capture exact dependency/controller versions; complete RB LEVEL
1 before any live data path; and conduct a separate IP review. The still-pending
Raspberry Pi milestone remains intact and is not recast as completed.
