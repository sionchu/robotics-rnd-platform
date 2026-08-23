# rbpodo and Rainbow RB Ecosystem Evaluation

Verified 2026-08-23. No RB controller was contacted. Evidence classes are
`OFFICIAL_DOC`, `SOURCE_INSPECTION`, and `ISSUE_EVIDENCE`; no live evidence is
present.

## Research questions

1. How can the platform control an RB-series cobot without exposing vendor API,
   units, response objects, or ROS types?
2. What does command acknowledgment mean, and how can completion remain truthful?
3. Which state and IO values are publicly evidenced?
4. Should direct control require ROS 2?

## Source identity and maintenance

### rbpodo

- Official repository: <https://github.com/RainbowRobotics/rbpodo>
- Reviewed release/tag: `v0.16.14`, released 2026-07-23
- Reviewed commit: `f6ef41adf629dd27c96b0d3e7ebf3d3fc0cc53c4`
- License: Apache-2.0, verified from `LICENSE`
- Languages: C++17 and Python bindings; package metadata includes Python 3.12
- PyPI: 0.16.14 wheels are published for CPython 3.8–3.12 on Windows x86-64
  and manylinux x86-64; no source distribution was listed for the release
- Maintenance snapshot: seven open issues and two open pull requests observed;
  latest reviewed release/commit was one month old
- Stability: README explicitly warns that the API is under development and
  subject to change

Evidence: `OFFICIAL_DOC`, `SOURCE_INSPECTION`.

### rbpodo_ros2

- Official repository: <https://github.com/RainbowRobotics/rbpodo_ros2>
- Reviewed revision: unreleased `main` at
  `5e8294a985e7ce5e20e70564c2681130afc5f502` (2026-06-23)
- Releases/tags: none observed
- Target documented by README: ROS 2 Humble
- Packages: bringup, robot description, ros2_control hardware plugin, MoveIt
  configuration, and custom messages/actions/services
- Stability: README states active development and says not to use it in production
- License: no root license and no GitHub-detected repository license. Package
  manifests mostly declare Apache-2.0; the MoveIt config declares BSD-3-Clause.

Evidence: `OFFICIAL_DOC`, `SOURCE_INSPECTION`. Aggregate license remains
`NOASSERTION`; the platform copies no code or descriptions.

### Official RB documentation

Reviewed official online manual/source at
<https://rainbowrobotics.github.io/rb_cobot_docs/> and repository revision
`bf23897e32e2`. Relevant pages include External Script Control API, UI Script
v6.10, reqdata v6.10, system variables, coordinate system, control-box/tool IO,
operation mode, TCP/tool, and safety/setup guidance. The documentation repository
has no detected license, so it is reference-only and facts are paraphrased.

## Connection model

`SOURCE_INSPECTION`: `rb::podo::Cobot(address, port)` constructs a TCP socket and
synchronously connects to command port 5000 by default. `CobotData` separately
connects to data port 5001. Invalid address or connect failure raises a runtime
error in the C++ layer. The socket is then non-blocking, but the constructor does
not expose a connect timeout and the public class has no reconnect API.

`OFFICIAL_DOC`: port 5000 accepts script commands and returns response/event
messages; port 5001 returns a binary state structure after `reqdata`.

Adapter consequence: live construction is optional and isolated; reconnect
creates new vendor objects, re-reads state, invalidates pending commands, and
keeps motion locked until application acknowledgment. The platform serializes
vendor calls because no thread-safety guarantee was found.

## Command, response, and completion model

`OFFICIAL_DOC`/`SOURCE_INSPECTION`: many commands, including `move_j` and
`move_l`, send a textual command and wait for an ACK. The ACK indicates command
receipt/execution acknowledgment; it is not proof that motion finished. Move
start/finish waits consume broadcast `motion_changed` informational events.
`ReturnType` distinguishes `Success`, `Timeout`, and `Error`; responses distinguish
ACK, info, warning, error, and unknown messages.

There is no public per-motion command identifier. Multiple processes receive
events, and the official README warns that an unrelated error from another
client can cause a wait with `return_on_error=true` to return. It also requires
flushing buffered responses before a move/wait sequence to avoid mistaking an
old event for the current motion.

Adapter consequence:

- command IDs and lifecycle transitions are platform-owned;
- ACK maps only to `ACCEPTED`, never `COMPLETED`;
- completion requires a current finish event and/or state evidence;
- timeout or connection loss during motion maps to `UNKNOWN`, not success;
- old messages are drained at a bounded command boundary where supported;
- one serialized command session is assumed; multi-client behavior remains a risk.

## State model

`SOURCE_INSPECTION`/`OFFICIAL_DOC`: the data channel exposes reference and
measured six-joint arrays, joint current, reference/measured TCP six-vectors,
four box analog inputs/outputs, sixteen box digital inputs/outputs, task and
robot states, speed ratio, power/initialization/collision indicators, two tool
digital inputs/outputs, tool voltage, and other controller fields. Joint values
are degrees; TCP translation is millimetres and rotation degrees. The current
adapter deliberately maps only the neutral subset it can represent: joint
positions, TCP pose, task/motion state, digital IO, speed ratio, and selected
fault/liveness context. Unsupported fields remain absent rather than guessed.

The data channel provides no documented source timestamp in the reviewed
structure. Platform snapshots therefore preserve a host receipt timestamp and
leave source timestamp `None`.

## IO model

`OFFICIAL_DOC`/`SOURCE_INSPECTION`: the control box provides sixteen digital
inputs and sixteen digital outputs indexed 0–15, plus four analog inputs/outputs
indexed 0–3. The reviewed state structure exposes two legacy tool digital
inputs/outputs and tool analog inputs, while official hardware documentation
shows model-version-dependent tool flange layouts. The v0.3 generic contract
therefore promotes only box digital IO; tool/analog/extended IO require explicit
capabilities and future model evidence.

Writes call the documented `set_box_dout` surface only when the adapter is not
read-only. IO writing is disabled by default and is not part of LEVEL 1.

## Pose and unit conventions

`OFFICIAL_DOC`: rbpodo `Point` is `[x, y, z, rx, ry, rz]`; translation is
millimetres and orientation uses Euler ZYX angles in degrees while retaining
the vector's xyz component order. Joint positions/speeds/accelerations use
degrees, degrees/second, and degrees/second². Linear motion speed/acceleration
use millimetres/second and millimetres/second².

The adapter alone converts:

- mm ↔ m;
- degrees ↔ radians;
- Euler ZYX ↔ normalized platform XYZW quaternion;
- vendor base coordinates ↔ an explicitly configured platform base `FrameId`.

Euler decomposition is non-unique at gimbal lock, so experiment 013 validates
rotation-matrix equivalence rather than equality of one Euler tuple.

## Motion and stop scope

The official surface contains many motion, configuration, program, realtime,
welding, gripper, and safety-related functions. v0.3 maps only joint motion,
linear motion, pause/resume, controlled software stop, state, and box digital
IO. It does not expose activation, brake release, operation-mode changes,
payload/TCP/user-frame writes, collision settings, realtime scripts, program
upload, or advanced motion.

Official external-script guidance recommends pause before task stop because a
stop during fast motion may be abrupt. The adapter's future controlled-stop
mapping is not an emergency stop and is not safety-rated. It remains
`HARDWARE_NOT_VALIDATED`.

## Public issue evidence

- [rbpodo PR 6](https://github.com/RainbowRobotics/rbpodo/pull/6) changed examples
  and source around flushing before move/wait. Cross-checked with the current
  README/changelog/source. `ISSUE_EVIDENCE` + `SOURCE_INSPECTION`.
- [rbpodo issue 7](https://github.com/RainbowRobotics/rbpodo/issues/7) reported a
  parsing error resolved after a controller update. It supports explicit
  controller/library compatibility recording, not a universal firmware claim.
- [rbpodo issue 15](https://github.com/RainbowRobotics/rbpodo/issues/15) reported
  incorrect Python joint-array behavior resolved by a NumPy upgrade, supporting
  Python/NumPy compatibility tests.
- [rbpodo issue 20](https://github.com/RainbowRobotics/rbpodo/issues/20) reports
  intermittent TCP fragmentation/parsing concerns. It has no maintainer
  resolution; treat it as an open transport risk, not confirmed controller behavior.
- [rbpodo issue 22](https://github.com/RainbowRobotics/rbpodo/issues/22) reports
  command-name drift. Current reviewed source uses the documented
  `set_speed_multiply` spelling; version-specific compatibility checks remain necessary.
- [rbpodo_ros2 issue 6](https://github.com/RainbowRobotics/rbpodo_ros2/issues/6)
  reports a TCP disconnect despite ping. It closed without public diagnosis and
  only reinforces conservative reconnect semantics.

## Direct rbpodo vs rbpodo_ros2 vs platform boundary

| Concern | Direct rbpodo | rbpodo_ros2 | Platform interface + optional bridge |
|---|---|---|---|
| Dependencies | C++/Python binding | rbpodo + Humble + ros2_control + MoveIt stack | NumPy core; rbpodo optional only in adapter |
| Latency path | Direct TCP client | controller manager/read-write/action path | Direct adapter now; optional bridge later |
| Deployment | Small but vendor-specific | ROS workspace and model/config packages | Mock/replay work without ROS/vendor package |
| API stability | Explicitly evolving | Active development, unreleased | Stable platform-owned contracts |
| Hardware-free testing | Requires fakes | Some fake hardware paths; ROS required | Contract suite across mock/replay/fake backend |
| ROS tooling | None | URDF, RViz, ros2_control, MoveIt | Future opt-in mapping |
| HMI suitability | Vendor types leak if used directly | ROS concepts become application API | HMI consumes RobotApplicationService only |
| Decision | `WRAP_WITH_ADAPTER` | `REFERENCE_ONLY` | `PROMOTE_TO_PLATFORM` after software experiments |

## Decision

`rbpodo`: `WRAP_WITH_ADAPTER`.

`rbpodo_ros2`: `REFERENCE_ONLY` pending a Jazzy-compatible released/licensed
revision and a concrete planning/control requirement.

Platform command/state/fault/journal/service logic is independently implemented;
`code_copied: false`. Hardware validation remains `LEVEL 0`.
