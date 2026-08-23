"""Optional rbpodo integration isolated behind the Rainbow backend protocol.

Importing this module does not import rbpodo, open a socket, or send a command.
The vendor constructor performs its own synchronous socket connection; callers
must therefore keep live use outside unattended processes until that behavior is
independently validated on the approved controller/network combination.
"""

from __future__ import annotations

from importlib import import_module, metadata
from typing import Any

from .backend import VendorCommandOutcome, VendorState


class RbpodoBackend:
    SUPPORTED_VERSIONS = frozenset({"0.16.14"})

    def __init__(self, host: str, command_port: int = 5000, data_port: int = 5001) -> None:
        if not host.strip():
            raise ValueError("rbpodo host is required")
        self._host = host
        self._command_port = command_port
        self._data_port = data_port
        self._module: Any = None
        self._robot: Any = None
        self._collector: Any = None
        self._data: Any = None

    @property
    def name(self) -> str:
        return "rbpodo"

    @property
    def version(self) -> str:
        try:
            return metadata.version("rbpodo")
        except metadata.PackageNotFoundError:
            return "not-installed"

    def connect(self, timeout_s: float) -> None:
        del timeout_s  # rbpodo 0.16.14 exposes no constructor connect-timeout parameter.
        version = metadata.version("rbpodo")
        if version not in self.SUPPORTED_VERSIONS:
            raise RuntimeError(
                f"unsupported rbpodo version {version}; reviewed versions: "
                f"{', '.join(sorted(self.SUPPORTED_VERSIONS))}"
            )
        module = import_module("rbpodo")
        required_module_api = ("Cobot", "CobotData", "ResponseCollector", "ReturnType", "DigitalIOMode")
        missing_module_api = [name for name in required_module_api if not hasattr(module, name)]
        if missing_module_api:
            raise RuntimeError(f"rbpodo is missing required API: {', '.join(missing_module_api)}")
        robot = module.Cobot(self._host, self._command_port)
        data = module.CobotData(self._host, self._data_port)
        required_robot_api = (
            "flush",
            "move_j",
            "move_l",
            "wait_for_move_started",
            "wait_for_move_finished",
            "task_pause",
            "task_stop",
            "task_resume",
            "set_box_dout",
        )
        missing_robot_api = [name for name in required_robot_api if not hasattr(robot, name)]
        if missing_robot_api:
            raise RuntimeError(f"rbpodo Cobot is missing required API: {', '.join(missing_robot_api)}")
        self._module = module
        self._robot = robot
        self._collector = module.ResponseCollector()
        self._data = data

    def disconnect(self) -> None:
        # rbpodo 0.16.14 exposes no explicit close method; releasing the objects
        # delegates socket teardown to their native destructors.
        self._data = None
        self._collector = None
        self._robot = None
        self._module = None

    def _require(self) -> tuple[Any, Any, Any]:
        if self._robot is None or self._collector is None or self._module is None:
            raise RuntimeError("rbpodo backend is disconnected")
        return self._robot, self._collector, self._module

    def _outcome(self, result: Any, *, completed: bool, message: str) -> VendorCommandOutcome:
        _, _, module = self._require()
        result_type = result.type()
        if result_type == module.ReturnType.Success:
            return VendorCommandOutcome(True, completed, message)
        if result_type == module.ReturnType.Timeout:
            return VendorCommandOutcome(True, False, "rbpodo response timeout", "TIMEOUT", True)
        return VendorCommandOutcome(False, False, "rbpodo reported an error", "VENDOR_ERROR")

    def read_state(self, timeout_s: float) -> VendorState:
        if self._data is None:
            raise RuntimeError("rbpodo data channel is disconnected")
        data = self._data.request_data(timeout_s).sdata
        robot_state = int(data.robot_state)
        task_state = int(data.task_state)
        mode = "MOVING" if robot_state == 3 or robot_state >= 60 else "IDLE"
        if task_state == 2:
            mode = "PAUSED"
        tcp_values = tuple(float(value) for value in data.tcp_pos)
        if len(tcp_values) != 6:
            raise ValueError(f"rbpodo returned {len(tcp_values)} TCP values; expected 6")
        tcp_pose = (
            tcp_values[0],
            tcp_values[1],
            tcp_values[2],
            tcp_values[3],
            tcp_values[4],
            tcp_values[5],
        )
        return VendorState(
            connected=True,
            joint_angles_deg=tuple(float(value) for value in data.jnt_ang),
            tcp_pose_mm_deg=tcp_pose,
            robot_state=mode,
            task_state=task_state,
            speed_ratio=float(data.default_speed),
            digital_inputs=tuple(bool(value) for value in data.digital_in),
            digital_outputs=tuple(bool(value) for value in data.digital_out),
            source_timestamp=None,
        )

    def _wait_for_motion(self, timeout_s: float) -> VendorCommandOutcome:
        robot, collector, _ = self._require()
        started = self._outcome(
            robot.wait_for_move_started(collector, timeout_s, True),
            completed=False,
            message="rbpodo motion started",
        )
        if not started.accepted or started.timed_out:
            return started
        return self._outcome(
            robot.wait_for_move_finished(collector, timeout_s, True),
            completed=True,
            message="rbpodo motion finished",
        )

    def move_joint(
        self,
        positions_deg: tuple[float, ...],
        speed_deg_s: float,
        acceleration_deg_s2: float,
        timeout_s: float,
    ) -> VendorCommandOutcome:
        robot, collector, _ = self._require()
        robot.flush(collector)
        accepted = self._outcome(
            robot.move_j(
                collector,
                list(positions_deg),
                speed_deg_s,
                acceleration_deg_s2,
                timeout_s,
                True,
            ),
            completed=False,
            message="rbpodo accepted joint motion",
        )
        return self._wait_for_motion(timeout_s) if accepted.accepted else accepted

    def move_linear(
        self,
        pose_mm_deg: tuple[float, float, float, float, float, float],
        speed_mm_s: float,
        acceleration_mm_s2: float,
        timeout_s: float,
    ) -> VendorCommandOutcome:
        robot, collector, _ = self._require()
        robot.flush(collector)
        accepted = self._outcome(
            robot.move_l(
                collector,
                list(pose_mm_deg),
                speed_mm_s,
                acceleration_mm_s2,
                timeout_s,
                True,
            ),
            completed=False,
            message="rbpodo accepted linear motion",
        )
        return self._wait_for_motion(timeout_s) if accepted.accepted else accepted

    def stop(self, timeout_s: float) -> VendorCommandOutcome:
        robot, collector, _ = self._require()
        # Official guidance recommends pause before task stop; this is not an E-stop.
        paused = self._outcome(
            robot.task_pause(collector, timeout_s, True), completed=False, message="rbpodo task paused"
        )
        if not paused.accepted:
            return paused
        return self._outcome(
            robot.task_stop(collector, timeout_s, True), completed=True, message="rbpodo task stopped"
        )

    def pause(self, timeout_s: float) -> VendorCommandOutcome:
        robot, collector, _ = self._require()
        return self._outcome(
            robot.task_pause(collector, timeout_s, True), completed=True, message="rbpodo task paused"
        )

    def resume(self, timeout_s: float) -> VendorCommandOutcome:
        robot, collector, _ = self._require()
        return self._outcome(
            robot.task_resume(collector, False, timeout_s, True),
            completed=True,
            message="rbpodo task resumed",
        )

    def reset_fault(self, timeout_s: float) -> VendorCommandOutcome:
        del timeout_s
        return VendorCommandOutcome(
            False,
            False,
            "rbpodo 0.16.14 has no generic fault-reset command; use controller-specific recovery",
            "UNSUPPORTED_FAULT_RESET",
        )

    def write_digital_output(self, channel: int, value: bool, timeout_s: float) -> VendorCommandOutcome:
        robot, collector, module = self._require()
        mode = module.DigitalIOMode.High if value else module.DigitalIOMode.Low
        return self._outcome(
            robot.set_box_dout(collector, channel, mode, timeout_s, True),
            completed=True,
            message="rbpodo digital output updated",
        )
