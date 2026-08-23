# Raspberry Pi Camera Node Setup

## Safe inspection first

Configure an SSH alias named `pi-rnd` in the user's local SSH configuration.
Do not place the address, username, key path, or host fingerprint in this
repository. Then run from the laptop:

```bash
./scripts/pi/doctor_pi.sh \
  --output datasets/local/pi_camera/hardware-manifest.json
```

The command uses batch authentication and strict host-key checking. It records
only a sanitized board/OS/kernel/Python/camera-stack manifest. It does not
change the Pi.

Inspect directly on the Pi when needed:

```bash
cat /etc/os-release
uname -sr
uname -m
python3 --version
rpicam-hello --version
rpicam-hello --list-cameras
python3 -c 'import picamera2; print(picamera2.__version__)'
python3 -c 'import cv2; print(cv2.__version__)'
```

Record the detected sensor and modes. Do not infer Camera Module 1/2/3/HQ from
the user's description.

## OS and packages

Preserve a stable working installation. Raspberry Pi OS 64-bit is preferred for
camera-first research because its current camera stack integrates libcamera,
`rpicam-apps`, and Picamera2, but this preference is not authority to re-image
or upgrade a working Pi.

If Picamera2 is absent on a supported current Raspberry Pi OS image, review the
official camera documentation and package policy before installing the vendor
package. Do not use `rpi-update`, disable SSH checks, run broad remote install
scripts, or perform a major OS upgrade in place for this milestone.

ROS 2 is not required on the Pi. The Ubuntu laptop remains the analysis, Git,
CI, and optional ROS 2 Jazzy workstation.

## Power, mount, and target gates

- Use a stable Pi 4 power supply and record throttling/temperature separately.
- Rigidly mount the camera and target for measurement runs.
- Print the generated target at 100%, disable fit-to-page, then measure the
  black outer square. The measured size—not the SVG nominal size—enters PnP.
- Keep raw frames and actual hardware manifests in ignored local storage.
