# Experiment 015 — RB Fault and Reconnect

## Question

Does connection ambiguity conservatively block future motion until synchronized
state is reviewed, without silently completing or resuming an outstanding command?

## Hypothesis

A dropped in-flight command becomes `UNKNOWN`; reconnect synchronizes state but
keeps motion locked until explicit acknowledgement; no automatic resume occurs.

## Sources

rbpodo connection behavior and public disconnect reports recorded in
`docs/research/RBPODO_INTEGRATION_RISKS.md`.

## Environment

Ubuntu 24.04, Python 3.12, deterministic fake backend; no network or hardware.

## Method

Inject connect timeout, in-command drop, reconnect, blocked retry, explicit
resync acknowledgement, a new command, and stale-state evidence.

## Evidence class

`MOCK_VERIFIED` only.

## Metrics

Status/error codes, connection state, motion lock, explicit recovery, resume calls.

## Results

All seven acceptance gates passed in `results/metrics.json`.

## Limitations

No physical network partition, controller queue, power cycle, or firmware was tested.

## Conclusion

Uncertain work remains unknown and reconnect cannot silently resume it.

## Decision

`PROMOTE_TO_PLATFORM`
