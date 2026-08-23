# Pi Camera Lab Checklist

## Before capture

- [ ] `pi-rnd` SSH alias works with strict host-key checking.
- [ ] Sanitized hardware manifest captured outside Git.
- [ ] Actual board, OS/kernel, sensor, modes, and software versions recorded.
- [ ] Stable power, storage space, temperature/throttling method checked.
- [ ] One full-frame/no-custom-crop camera mode selected.

## Camera mounting

- [ ] Camera and cable are rigid and strain-relieved.
- [ ] Camera reference point is defined in notes.
- [ ] Camera is not moved between calibration and validation unintentionally.

## Target printing and measuring

- [ ] SVG generated for `tag36h11`, id 7.
- [ ] Printed at 100%; fit-to-page disabled.
- [ ] 100 mm reference measured.
- [ ] Outer black tag size measured in metres with tool resolution/uncertainty.
- [ ] Checkerboard square size measured if calibration uses checkerboard.

## Lighting and controls

- [ ] Glare/flicker avoided; no unsafe light source.
- [ ] Auto sequence warmed up and metadata inspected.
- [ ] Controlled values use only detected supported controls.
- [ ] Focus is changed only if the sensor/module exposes it.

## Calibration capture

- [ ] Centre/edges/near/far/tilt/roll coverage captured.
- [ ] Rejection criteria written before exclusion.
- [ ] Three independent calibration runs/subsets completed.
- [ ] Provenance binds sensor, mode, resolution, format, and crop.

## Repeatability capture

- [ ] Camera and tag rigid for 200 frames.
- [ ] Every failed detection retained.
- [ ] Capture metadata and timestamps retained per frame.

## Distance capture

- [ ] Only feasible distances used.
- [ ] Distance/reference point/uncertainty recorded per condition.
- [ ] Tag pixel size and detection rate retained.

## Angle capture

- [ ] Positive/negative angles physically reproducible.
- [ ] Nominal versus measured angle clearly classified.
- [ ] Uncertainty recorded or accuracy claim omitted.

## Dataset transfer and analysis

- [ ] Fetch dry-run reviewed, then executed without `--delete`.
- [ ] Dataset manifest/file validation passes.
- [ ] Pi and laptop use the same dataset/configuration.
- [ ] Repeatability and study JSON/CSV reproduced by commands.
- [ ] Optional plots show units and ground-truth class.

## Backup and conclusion

- [ ] Raw local data backed up outside Git.
- [ ] No address, serial, MAC, credential, private path, or capture staged.
- [ ] Each experiment conclusion records failures and limitations.
- [ ] Promotion decision is explicit; release tag remains blocked until gates pass.
