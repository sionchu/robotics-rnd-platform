# Experiment 014 — rbpodo Command Semantics

## Question

Can the platform preserve the difference among send, ACK/acceptance, motion
start, completion, timeout, and ambiguous/stale response consumption?

## Hypothesis

Only finish evidence will produce `COMPLETED`; a timeout after acceptance will
not; delayed, duplicate, and unexpected responses will remain diagnosable.

## Sources

rbpodo 0.16.14 source/README/changelog and public flush-before-wait PR, recorded
in `docs/research/RBPODO_EVALUATION.md` and its risk register.

## Environment

Ubuntu 24.04, Python 3.12, deterministic fake backend; no rbpodo runtime or controller.

## Method

Exercise normal completion, motion timeout, delayed response, duplicate response,
and unexpected response through the same adapter contract.

## Evidence class

`SOURCE_VERIFIED` and `MOCK_VERIFIED`; `LIVE_VERIFIED` is explicitly false.

## Metrics

Lifecycle terminal status and anomaly diagnostics retained per command.

## Results

All three acceptance gates passed in `results/metrics.json`.

## Limitations

The fake does not reproduce TCP scheduling, parser implementation, or controller timing.

## Conclusion

ACK and completion remain distinct and ambiguous evidence is never upgraded.

## Decision

`PROMOTE_TO_PLATFORM`
