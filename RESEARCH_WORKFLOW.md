# Research Workflow

```text
LEARN -> EXPERIMENT -> BENCHMARK / VERIFY -> PACKAGE -> APPLICATION
```

## 1. Learn

Record the theory, units, frames, assumptions, official sources, and a small
runnable exercise in `learning/`. Completion means understanding can be shown by
an example or explanation, not merely that a link was saved.

## 2. Experiment

Create a dated directory with `scripts/new_experiment.py`. State one falsifiable
question and hypothesis. Pin the environment and random seed where relevant.
Keep exploratory dependencies and interfaces out of the reusable package.

## 3. Benchmark / verify

Define metrics before interpreting results. Record latency distribution, memory,
accuracy/error, dataset or fixture provenance, hardware, warm-up, sample count,
and failure cases as applicable. Compare CPU/GPU/edge targets only with the same
inputs and documented settings. A failed hypothesis can still be a useful result.

## 4. Package

Promotion requires a stable neutral API, explicit units/frames, deterministic
tests, error behavior, architecture review, dependency justification, and a
conclusion choosing `discard`, `continue`, or `package`. Hardware algorithms also
need replay or synthetic verification where practical.

## 5. Application

Applications choose adapters and configuration at the composition root. They do
not push vendor, ROS, GUI, or process-specific types back into core. Record real
hardware validation separately from mock, replay, and simulation results.

When hardware is unavailable, prepare schemas, adapters, replay, tests, and an
exact handoff, but keep measurements null and use
`NOT_RUN_HARDWARE_UNAVAILABLE`. Hardware-dependent release tags and promotion
remain blocked until physical evidence exists.

## Graduation checklist

- Question, hypothesis, environment, reproduction steps, metrics, observations,
  conclusion, and decision are complete.
- Data and external code licenses/provenance are reviewed.
- Sensitive/company/vendor assets remain outside Git.
- Tests cover normal, invalid, and failure paths.
- Performance and numerical limitations are documented.
- An ADR exists when the change introduces a lasting architecture decision.
