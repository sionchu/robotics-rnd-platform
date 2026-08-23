# Exact Raspberry Pi Camera Hardware Handoff

Status on 2026-08-23: `PI_UNREACHABLE`; no authenticated session was available
through `ROBOTICS_RND_PI_HOST` or the default `pi-rnd` alias. No network scan,
host-key bypass, remote change, sensor assumption, or physical measurement was
performed.

## Gate 1 — Configure reachability locally

Create/review an SSH alias named `pi-rnd` outside the repository. Use the actual
user, address, key, and first-contact fingerprint verification there. Do not
paste those values into Git or experiment notes.

```bash
export ROBOTICS_RND_PI_HOST=pi-rnd
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes "$ROBOTICS_RND_PI_HOST" true
```

Stop if authentication or host verification fails. Do not disable checks.

## Gate 2 — Read-only environment and camera discovery

```bash
mkdir -p datasets/local/pi_camera
./scripts/pi/doctor_pi.sh \
  --output datasets/local/pi_camera/hardware-manifest.json
python -m json.tool datasets/local/pi_camera/hardware-manifest.json
```

Confirm actual Pi model/architecture/OS/kernel/Python, `rpicam-apps`, Picamera2,
OpenCV, detected sensor, and modes. Stop and diagnose if `rpicam-hello
--list-cameras` does not report a camera. Do not assume a module revision.

## Gate 3 — Generate and measure targets

```bash
python scripts/generate_apriltag_target.py \
  --family tag36h11 --tag-id 7 --nominal-tag-size-mm 120 \
  --output datasets/local/pi_camera/apriltag-36h11-id7.svg
cp experiments/vision/_physical_measurement_template.yaml \
  datasets/local/pi_camera/physical-measurements.yaml
```

Print at 100% with fit-to-page disabled. Measure the 100 mm reference, outer
black tag square, and calibration target. Fill the local measurement file with
tool resolution, uncertainty, and camera reference definition.

## Gate 4 — Dry-run and perform minimal deployment

```bash
./scripts/pi/deploy_pi.sh
./scripts/pi/deploy_pi.sh --execute
```

On the Pi, inspect `deployment-manifest.json`, create the selected isolated
Python environment, and install the copied wheel. Use the OS-supported
Picamera2/libcamera packages. Record actual versions; do not copy the laptop
virtual environment or compiled x86 wheels.

## Gate 5 — Bring-up and controlled capture

Substitute the exact camera mode reported in Gate 2:

```bash
./scripts/pi/capture_dataset.sh \
  --output robotics-rnd-data/pi-camera-auto-001 \
  --camera-mode '<exact detected mode>' --frames 100
./scripts/pi/fetch_dataset.sh \
  --remote-session robotics-rnd-data/pi-camera-auto-001
./scripts/pi/fetch_dataset.sh \
  --remote-session robotics-rnd-data/pi-camera-auto-001 --execute
python -m robotics_rnd.edge validate-dataset \
  --dataset datasets/local/pi_camera/pi-camera-auto-001
```

Inspect exposure/gain/colour/focus metadata after warm-up. If supported, run a
new controlled session with explicit values via `python3 -m robotics_rnd.edge
capture` on the Pi. Never overwrite the auto session.

## Gate 6 — Calibration

Rigidly capture deliberate checkerboard coverage and create three independent
calibration runs. Use measured square size. Save a
`robotics-rnd-calibration-artifact-v1` bound to detected sensor, exact mode,
capture/calibration resolution, BGR888, and crop. Do not reuse v0.2 synthetic
intrinsics or an artifact from another mode.

For each of three independently captured calibration sessions:

```bash
python -m robotics_rnd.edge calibrate-dataset \
  --dataset datasets/local/pi_camera/<calibration-session-1> \
  --sensor-model '<detected sensor>' \
  --columns 9 --rows 6 \
  --square-size-m <measured_square_metres> \
  --measurement-uncertainty '<tool resolution and estimated uncertainty>' \
  --output datasets/local/pi_camera/calibration-1.json
```

Then compare the three bound artifacts:

```bash
python -m robotics_rnd.edge compare-calibrations \
  --artifact datasets/local/pi_camera/calibration-1.json \
  --artifact datasets/local/pi_camera/calibration-2.json \
  --artifact datasets/local/pi_camera/calibration-3.json \
  --output datasets/local/pi_camera/calibration-repeatability.json
```

Run the resolution/mode/provenance tests before PnP. Record all three intrinsic,
distortion, reprojection, and between-run results in experiment 007.

## Gate 7 — Real AprilTag/PnP and studies

For each local session, substitute the detected sensor, valid calibration, and
measured tag size:

```bash
python -m robotics_rnd.edge process \
  --dataset datasets/local/pi_camera/<session-id> \
  --calibration datasets/local/pi_camera/<calibration-artifact.json> \
  --sensor-model '<detected sensor>' \
  --tag-size-m <measured_metres> \
  --tag-family tag36h11 --tag-id 7 \
  --output datasets/local/pi_camera/<session-id>/laptop-pose-run.json
```

Execute experiment 008 (200 static frames), feasible experiment 009 distances,
reproducible experiment 010 angles, and safe experiment 011 capture conditions.
Aggregate runs with:

```bash
python scripts/analyze_pi_camera_study.py \
  --factor distance_m \
  --run 0.5=datasets/local/pi_camera/<0.5m-session>/laptop-pose-run.json \
  --run 1.0=datasets/local/pi_camera/<1.0m-session>/laptop-pose-run.json \
  --output-json datasets/local/pi_camera/distance-summary.json \
  --output-csv datasets/local/pi_camera/distance-summary.csv
```

## Gate 8 — Pi versus laptop

Run `robotics_rnd.edge benchmark` on the Pi against the transferred/captured
session and on the laptop against the exact same PNG/metadata files. Retain both
pose-run sidecars and benchmark JSON. Then:

```bash
python -m robotics_rnd.edge compare-runs \
  --reference datasets/local/pi_camera/<session-id>/pi-pose-run.json \
  --candidate datasets/local/pi_camera/<session-id>/laptop-pose-run.json \
  --output datasets/local/pi_camera/<session-id>/equivalence.json
```

Record Python/OpenCV versions, CPU/memory measurement method, warm-up, thermal
state, latency/FPS, detection disagreements, and maximum corner/translation/
orientation differences in experiment 012.

## Gate 9 — Promotion and release

Run `./scripts/test_all.sh`, pre-commit, repository/IP/size audit, and GitHub CI.
Replace `NOT_RUN_HARDWARE_UNAVAILABLE` only with real sanitized summaries.
Promote only components supported by evidence. Create and push
`v0.2.1-pi-camera-edge-lab` only after all applicable physical gates pass; the
preparation-only state must remain untagged.
