# Datasets

Raw and processed research data are intentionally local-only. Raspberry Pi
camera sessions use:

```text
datasets/local/pi_camera/<neutral-session-id>/
  manifest.json
  frames/
  metadata/
  ground_truth.csv
  notes.md
```

`datasets/local/**` is ignored. Commit schemas, sanitized result summaries, and
small independently generated fixtures only—never physical captures, hardware
identifiers, addresses, or private calibration artifacts.

Only provenance, schema, license, split, checksum, and retrieval instructions are
tracked. Raw/processed datasets remain ignored. Never store company/private
images, clouds, CAD-derived data, or operational captures here.
