# Experiments

Create experiments with:

```bash
python scripts/new_experiment.py "short hypothesis name"
```

Keep exploratory code, dependencies, generated results, and uncertainty here
until the promotion gate in `RESEARCH_WORKFLOW.md` is satisfied. Retain failed
experiments when the conclusion prevents repeated work.

Reproduce the v0.3 software-only robot-control studies with:

```bash
python -m experiments.robot.run_all verify
```

Their `SOURCE_VERIFIED` and `MOCK_VERIFIED` evidence is not live robot evidence.
