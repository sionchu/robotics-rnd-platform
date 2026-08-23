# RB Robot Control Lab

Goal: validate the generic robot contract against a supported Rainbow controller
without coupling job logic, GUI, or vision to `rbpodo`.

Milestones: official version review -> read-only connection/state -> simulation ->
capability/error mapping -> stop/fault behavior -> joint motion -> linear motion ->
digital I/O -> logging/replay -> supervised hardware acceptance. Every live stage
requires an explicit safety procedure and opt-in tests.

Future HMI composition:

```text
HMI -> job state machine -> RobotInterface -> RainbowRobotDriver
                       \-> VisionInterface -> selected provider
```
