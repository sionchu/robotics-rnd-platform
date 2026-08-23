# Robot control

Learn state/capabilities, joint/cartesian commands, trajectories, I/O, timeouts,
faults, stops, safety, and observability. Exercise: extend `MockRobot` contracts,
then simulator/replay. Live RB work comes only after safety review.

The v0.3 executable exercise is:

```bash
python -m robotics_rnd.rb mock-demo
python -m robotics_rnd.rb fault-demo
python -m experiments.robot.run_all verify
```

Explain why ACK is not completion, why an ambiguous in-flight command becomes
`UNKNOWN`, why reconnect cannot auto-resume, and why software stop is not an
emergency stop. These exercises demonstrate software understanding only.
