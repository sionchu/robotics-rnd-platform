# Exact RB LEVEL 1 Read-Only Hardware Handoff

Status: `NOT_RUN_HARDWARE_UNAVAILABLE`. This procedure stops at LEVEL 1. It does
not authorize motion, IO writes, controller configuration, activation, brake
release, program execution, or safety-setting changes.

## Gate 1 — Authorization and physical safety review

Confirm robot owner/operator authorization, trained responsible person, exact
robot/control-box documentation, physical emergency-stop access, stable power,
and that no process/application will issue commands concurrently. If any point
is uncertain, stop.

## Gate 2 — Local untracked configuration

Create `~/.config/robotics-rnd/rainbow.toml` outside Git with the reviewed local
address and these mandatory values:

```toml
[robot]
driver = "rainbow"
mode = "READ_ONLY"
motion_enabled = false
auto_reconnect = false
```

Never paste the real address, serial, or topology into repository files/logs.

## Gate 3 — Version and provenance capture

In a separate reviewed environment, record sanitized values locally:

```bash
python3 --version
python3 -m pip show rbpodo
python3 -c 'import importlib.metadata as m; print(m.version("rbpodo"))'
```

Record robot model class, controller software/firmware version, and relevant
official document version without serial numbers. Compare them with
`RB_COMPATIBILITY_MATRIX.md`. Stop on an unreviewed rbpodo version.

## Gate 4 — Network check without scanning

Use only the owner-provided address. Do not scan a subnet. Confirm reachability
with an owner-approved method and verify that no other external control client is
active. Do not disable controller security/safety functions.

## Gate 5 — Adapter preflight with fake backend

From the repository environment:

```bash
python -m robotics_rnd.rb capabilities
python -m robotics_rnd.rb mock-demo
python -m robotics_rnd.rb fault-demo
python -m experiments.robot.run_all verify
```

Confirm `hardware_validation_level` remains `LEVEL 0` and no command exposes a
live move path.

## Gate 6 — Reviewed read-only connection utility

Implement/review a separate LEVEL 1 command only after Gates 1–5. It must load
the untracked config, force `READ_ONLY`, force `motion_enabled=false`, redact the
address, use bounded state-read timeouts, and require an explicit operator
confirmation. Do not reuse the mock-demo command for hardware.

## Gate 7 — Read-only observations

Connect once, then collect only:

- adapter/rbpodo/controller versions;
- capability discovery;
- connection/liveness status;
- joint and TCP state with units/frame noted;
- box digital input/output state as reads;
- repeated bounded state reads and receipt timestamps.

No write API should be callable. Verify a rejected motion and rejected IO-write
through local guard logic without asking the backend to transmit them.

## Gate 8 — Disconnect and ambiguity check

Disconnect cleanly, confirm no background thread/socket remains, and verify that
application state is `OFFLINE`. If any call timed out or the connection dropped,
record it as a communication fault; never infer command completion.

## Gate 9 — Sanitize, test, and decide

Keep raw local logs outside Git. Commit only a sanitized summary with:

```yaml
hardware_validation_level: LEVEL 1
live_motion: false
io_write: false
configuration_write: false
measurements:
  state_read_success_rate: <measured>
  state_read_latency_method: <documented>
  connection_recovery: NOT_RUN
```

Rerun all tests/CI. Update the compatibility matrix and risks. A separate future
prompt must authorize and define LEVEL 2 or LEVEL 3; do not proceed automatically.
