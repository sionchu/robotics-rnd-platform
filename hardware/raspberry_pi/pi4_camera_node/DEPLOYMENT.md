# Headless Deployment and Dataset Flow

## 1. Dry-run the minimal wheel transfer

```bash
./scripts/pi/deploy_pi.sh
./scripts/pi/deploy_pi.sh --execute
```

The script builds an architecture-independent Python wheel on the laptop and
copies only that wheel plus `deployment-manifest.json`. It never uses `--delete`
and never installs packages remotely. Picamera2 should come from the supported
Pi OS environment; compiled OpenCV packages must be installed/built separately
for ARM64 and must not be copied from x86_64.

On the Pi, inspect the copied manifest, create an isolated environment that can
access the system Picamera2 package if required, and install the wheel. Record
the actual Python/OpenCV/Picamera2 versions in the hardware manifest.

## 2. Capture

```bash
./scripts/pi/capture_dataset.sh \
  --output robotics-rnd-data/pi-camera-<UTC-session> \
  --camera-mode '<exact detected mode label>' \
  --frames 200
```

The output contains:

```text
manifest.json
frames/000000.png
metadata/000000.json
ground_truth.csv        # user-created only when a physical reference exists
notes.md                # user-created lab notes
```

## 3. Fetch without deleting remote data

```bash
./scripts/pi/fetch_dataset.sh \
  --remote-session robotics-rnd-data/<session-id>
./scripts/pi/fetch_dataset.sh \
  --remote-session robotics-rnd-data/<session-id> \
  --execute
```

## 4. Validate and replay on the laptop

```bash
python -m robotics_rnd.edge validate-dataset \
  --dataset datasets/local/pi_camera/<session-id>

python -m robotics_rnd.edge process \
  --dataset datasets/local/pi_camera/<session-id> \
  --calibration datasets/local/pi_camera/<calibration-artifact.json> \
  --sensor-model '<detected sensor>' \
  --tag-size-m <measured outer black square in metres> \
  --output datasets/local/pi_camera/<session-id>/laptop-pose-run.json
```

Run the same `benchmark` subcommand on the Pi and laptop against the same
dataset. Compare the resulting pose-run files with the platform comparison
utility/tests; do not compare different captures.
