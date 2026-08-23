# Raspberry Pi 4 Deployment Target

The Pi is an edge target, not the architecture center. Select Raspberry Pi OS
64-bit or Ubuntu only after checking camera, ROS 2, Python, and deployment needs.
Use SSH keys and host aliases outside the repository; never commit addresses or
credentials.

Initial lab plan:

1. Record OS/kernel/Python/camera/thermal/power versions.
2. Validate `rpicam-apps`/libcamera or the chosen Ubuntu camera path.
3. Deploy a minimal wheel or source checkout in an isolated environment.
4. Run a recorded-image CPU baseline, then camera acquisition.
5. Measure latency distribution, FPS, memory, CPU, temperature, and accuracy.
6. Compare identical fixtures on laptop CPU, laptop GPU if available, Pi CPU,
   and a future Jetson.
7. Add ROS 2 deployment only after the direct benchmark is stable.

See `resources/raspberry_pi.md`. GPIO/camera libraries stay in adapters.
