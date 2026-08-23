# Experiment 016 — RB I/O Contract

## Question

Can the generic digital-I/O abstraction represent publicly documented Rainbow
control-box I/O without inventing tool-I/O portability?

## Hypothesis

Sixteen zero-based boolean inputs/outputs will map deterministically; channel 16
will fail; read-only and tool-I/O capabilities will not be over-claimed.

## Sources

rbpodo `SystemState::Data` and `set_box_dout` public source, recorded in
`docs/research/RBPODO_EVALUATION.md`.

## Environment

Ubuntu 24.04, Python 3.12, deterministic fake backend; no wiring or controller.

## Method

Write alternating values on channels 0–15, read back state, try channel 16, and
inspect read-only and tool capability declarations.

## Evidence class

`SOURCE_VERIFIED` and `MOCK_VERIFIED`.

## Metrics

Successful round trips, invalid-channel error, capability-set constraints, call count.

## Results

All five acceptance gates passed in `results/metrics.json`.

## Limitations

Electrical level, latency, persistence, tool-flange I/O, analog I/O, and model
differences were not tested.

## Conclusion

Control-box digital I/O is generic; tool I/O remains unclaimed and model-dependent.

## Decision

`PROMOTE_TO_PLATFORM`
