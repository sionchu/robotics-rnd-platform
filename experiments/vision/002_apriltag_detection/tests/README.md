# Experiment tests

`tests/unit/test_apriltag_detection.py` covers deterministic generation, valid
detection, no-tag input, id, clockwise corner ordering, family validation, and
image replay/reset/exhaustion.

`fixtures/` contains six small generated PNGs. They contain no captures,
private metadata, or third-party images.
