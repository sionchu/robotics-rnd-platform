# Robot Control Safety Boundary

## Scope

The v0.3 control stack is an auditable research/application boundary, not a
safety controller. It prevents accidental capability exposure and false command
claims in software. It cannot replace controller safety functions, a risk
assessment, emergency stop, trained supervision, guarded workspace, or validated
payload/TCP/speed configuration.

```text
HMI / lab command
        |
        v
RobotApplicationService ---- JSONL journal ---- ReplayRobot
        |
        v
RobotInterface (SI units, framed poses, lifecycle/fault models)
        |
        +---- MockRobot
        +---- RainbowRobotDriver ---- FakeRainbowBackend
                                  \-- RbpodoBackend (optional, lazy, reviewed version only)
```

## Enforced software rules

- Default Rainbow configuration is `READ_ONLY`; motion and I/O writes are false.
- No CLI command accepts an address, constructs `RbpodoBackend`, connects live,
  or requests live motion.
- The optional vendor module is imported only during an explicit backend connect.
- Public interfaces contain no rbpodo/ROS types or vendor units.
- Backend calls are serialized. Command IDs and lifecycle are platform-owned.
- ACK/acceptance is not completion. Completion needs finish evidence.
- A timeout or connection drop cannot be silently upgraded to `COMPLETED`.
- A dropped in-flight command is `UNKNOWN`; reconnect synchronizes state, locks
  motion, and never resends/resumes it. Explicit stable-state acknowledgement is
  required before a new motion.
- Software stop maps to pause then task stop in the reviewed backend. It is named
  `CONTROLLED_STOP`, is not safety-rated, and is not an emergency stop.
- Control-box digital output is capability-gated and disabled by default. Tool,
  analog, payload, TCP, frame, activation, realtime-script, and safety-setting
  writes are not promoted.
- Journals use a portable schema and key-based redaction. Raw vendor messages,
  controller addresses, serials, tokens, and operational data do not belong in Git.

Operational rejection, timeout, controller/I/O faults, and connection loss use
`RobotResult` plus `RobotFaultRecord` categories (`COMMUNICATION`, `CONTROLLER`,
`MOTION`, `SAFETY`, `IO`, `CONFIGURATION`, `APPLICATION`, or `UNKNOWN`). Python
exceptions are reserved for invalid API usage/programming errors, unsupported
capabilities, invalid configuration, or unavailable adapter initialization.

Lifecycle evidence records whether a status is `VENDOR_REPORTED`,
`ADAPTER_DERIVED`, or `APPLICATION_DERIVED`. The adapter exposes bounded liveness
summaries—last successful state/response, connection age, and consecutive
communication failures—without creating an unjustified high-rate heartbeat.

## Evidence boundary

`SOURCE_VERIFIED` means a fact was cross-checked in official documentation/source.
`MOCK_VERIFIED` means platform behavior passed deterministic fake tests.
`REPLAY_TEST` means a platform journal reproduced deterministically. None means
physical timing, reachability, motion, stop distance, reliability, or compatibility.

Current state is `SOFTWARE_VALIDATED`, `HARDWARE_NOT_VALIDATED`,
`hardware_validation: false`, and `max_hardware_validation_level: 0`.

## Future physical gate

The only authorized next hardware stage is the exact LEVEL 1 read-only handoff in
`docs/research/RB_HARDWARE_HANDOFF.md`. A different future task must authorize
any non-motion write or motion. Failure of a software guard, version mismatch,
unbounded call, concurrent client, stale state, or uncertain ownership stops the gate.
