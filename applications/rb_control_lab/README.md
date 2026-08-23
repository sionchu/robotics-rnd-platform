# RB Control Lab

This application composes the platform-owned `RobotApplicationService` with the
Rainbow adapter, fake backend, journal, and replay driver. It contains no live
controller address and no live-connect or live-motion command.

Run the software-only paths after an editable install:

```bash
robotics-rnd-rb status
robotics-rnd-rb capabilities
robotics-rnd-rb mock-demo --journal /tmp/rb-mock-demo.jsonl
robotics-rnd-rb fault-demo
robotics-rnd-rb replay /tmp/rb-mock-demo.jsonl
```

The mock demo covers connect, state, joint-command mapping, control-box digital
output, stop, disconnect, JSONL audit evidence, and deterministic replay. The
fault demo proves that a connection drop makes the in-flight command `UNKNOWN`,
locks subsequent motion, and never auto-resumes it.

All output uses hardware validation level 0. See
`docs/research/RB_HARDWARE_HANDOFF.md` before any future physical work; the first
allowed stage is supervised, read-only LEVEL 1 validation.
