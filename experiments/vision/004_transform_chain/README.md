# Experiment 004 — Transform Chain Validation

Question: does the platform unambiguously compose camera observations into a
base frame?

One hundred deterministic random cases compare platform composition with direct
homogeneous-matrix multiplication and recover the original camera-to-tag
transform through the inverse chain.

```bash
python -m experiments.vision.run_all transform
```
