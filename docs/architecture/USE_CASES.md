# Platform Use Cases

## Future RB robot application rewrite

```text
Application/HMI -> Job engine -> RobotInterface -> RainbowRobotDriver -> rbpodo -> RB controller
```

The GUI, state/job logic, driver, vision provider, and skills are separate.
Applications see platform commands/results only. Capability discovery prevents
the HMI from presenting operations the validated adapter does not support.

## RB plus Mech-Mind vision guidance

```text
                    Guidance skill
                    /            \
          RobotInterface       VisionInterface
                |                   |
      RainbowRobotDriver       MechEyeDriver
                |                   |
             rbpodo          official camera SDK
```

If an external Mech-Vision project owns perception, substitute the distinct
`MechVisionProvider`; do not make a direct camera adapter impersonate it.

## Raspberry Pi vision experiment

```text
Pi camera adapter -> generic vision pipeline -> target/quality -> optional ROS 2 bridge
```

The same algorithm runs against laptop files/replay. Benchmarks record latency,
FPS, memory, and accuracy for laptop CPU, laptop GPU if available, Pi CPU, and a
future Jetson without changing core types.

## KAI Robotics Vision future consumption

KRV stays separate. Only after a generic package is stable, reviewed for
ownership, and organizationally approved should KRV consume a released/tagged
version. The personal platform never depends on KRV.

## NVIDIA portfolio extraction

A separate public repository may be created only after IP/security review. It
needs a generic problem statement, reproducible setup, architecture, tests,
benchmark, demo, limitations, licenses, and no company code/data or private
metadata.
