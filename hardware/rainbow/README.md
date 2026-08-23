# Rainbow Robotics Research Boundary

The current platform provides generic lifecycle/fault/state contracts, mock and
replay drivers, a read-only-by-default `RainbowRobotDriver`, an optional lazy
rbpodo backend, and a deterministic fake/fault backend. No RB controller, SDK
runtime, network, state, I/O, stop, or motion was accessed or validated.

Software mappings cover connect/disconnect, state, joint/linear commands,
controlled stop, pause/resume, box digital I/O, timeouts, capabilities, unit/pose
conversion, and conservative faults. They are `SOURCE_VERIFIED`/`MOCK_VERIFIED`,
not physical evidence. Do not expose `rbpodo` objects/enums.

Before live work follow `docs/research/RB_HARDWARE_HANDOFF.md`. The first and only
currently authorized stage is LEVEL 1 read-only: pin controller/firmware/SDK
versions, review safety/ownership, connect once, read bounded state/I/O, and
disconnect. Motion and all writes remain forbidden.

Target architecture:

```text
Linux HMI -> RobotApplicationService -> RobotInterface -> Rainbow adapter -> optional rbpodo
                         \-> JSONL journal -> ReplayRobot
```
