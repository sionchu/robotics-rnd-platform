# Rainbow Robotics Research Boundary

The current platform provides a generic robot contract, deterministic mock, and
an unavailable `RainbowRobotDriver` skeleton. No RB controller, SDK, or live
motion was accessed or validated.

Future mapping points: connect/disconnect; state; joint/linear motion; stop;
pause/resume if supported; reset fault; digital I/O; timeouts; capability
discovery; vendor error translation. Do not expose `rbpodo` objects/enums.

Before live work: pin controller/firmware/SDK versions; review official safety
and operating manuals; establish a physical E-stop and controlled workspace;
define speed/payload/tool limits; validate read-only state first; then simulation;
then supervised low-risk commands. Record results outside generic core tests.

Target architecture:

```text
Linux HMI -> Job engine -> RobotManager -> Rainbow adapter -> rbpodo -> RB controller
                         \-> VisionManager -> VisionInterface
```
