"""Transparent command construction and conservative subprocess ownership."""

from __future__ import annotations

import os
import queue
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .models import CommandSpec, ExperimentSummary


def format_command(argv: tuple[str, ...] | list[str]) -> str:
    return subprocess.list2cmdline(list(argv))


def format_spec(spec: CommandSpec) -> str:
    """Render the actual argv plus explicit environment overrides."""

    command = format_command(spec.argv)
    prefix = f"cd /d {subprocess.list2cmdline([str(spec.cwd)])}"
    if not spec.environment:
        return f"{prefix} && {command}"
    assignments = " && ".join(f'set "{name}={value}"' for name, value in spec.environment.items())
    return f"{prefix} && {assignments} && {command}"


def build_probe_command(
    *,
    repo_root: Path,
    isaac_lab_root: Path,
    experiment: ExperimentSummary,
    output_path: Path,
    device: str,
    instantiate: bool = True,
) -> CommandSpec:
    argv = [
        str(isaac_lab_root / "isaaclab.bat"),
        "-p",
        str(repo_root / "applications" / "robot_learning_workbench" / "isaac_probe.py"),
        "--mode",
        "task",
        "--registration",
        experiment.registration_module,
        "--task",
        experiment.task_id or "",
        "--output",
        str(output_path),
        "--device",
        device,
        "--headless",
    ]
    if instantiate:
        argv.append("--instantiate")
    return CommandSpec("Task Probe", tuple(argv), isaac_lab_root, output_path, {"PYTHONPATH": str(repo_root)})


def build_gui_command(
    *,
    repo_root: Path,
    isaac_lab_root: Path,
    experiment: ExperimentSummary,
    output_path: Path,
    seed: int,
    device: str,
    steps: int = 600,
) -> CommandSpec:
    argv = (
        str(isaac_lab_root / "isaaclab.bat"),
        "-p",
        str(repo_root / "applications" / "robot_learning_workbench" / "isaac_probe.py"),
        "--mode",
        "gui",
        "--registration",
        experiment.registration_module,
        "--task",
        experiment.play_task_id or experiment.task_id or "",
        "--output",
        str(output_path),
        "--seed",
        str(seed),
        "--steps",
        str(steps),
        "--device",
        device,
        "--viz",
        "kit",
    )
    return CommandSpec("Launch Task GUI", argv, isaac_lab_root, output_path, {"PYTHONPATH": str(repo_root)})


def build_train_command(
    *,
    repo_root: Path,
    isaac_lab_root: Path,
    experiment: ExperimentSummary,
    num_envs: int,
    iterations: int,
    seed: int,
    device: str,
    run_name: str,
    logger: str = "tensorboard",
    headless: bool = True,
) -> CommandSpec:
    argv = [
        str(isaac_lab_root / "isaaclab.bat"),
        "train",
        "--rl_library",
        "rsl_rl",
        "--task",
        experiment.task_id or "",
        "--num_envs",
        str(num_envs),
        "--max_iterations",
        str(iterations),
        "--seed",
        str(seed),
        "--logger",
        logger,
        "--run_name",
        run_name,
        "--device",
        device,
        "--deterministic",
        "--external_callback",
        f"{experiment.registration_module}.register_tasks",
    ]
    if headless:
        argv.insert(12, "--headless")
    return CommandSpec(
        f"PPO {iterations} iterations",
        tuple(argv),
        isaac_lab_root,
        environment={"PYTHONPATH": str(repo_root)},
    )


def build_metrics_command(
    *, repo_root: Path, isaac_lab_root: Path, run_dir: Path, output_path: Path
) -> CommandSpec:
    argv = (
        str(isaac_lab_root / "isaaclab.bat"),
        "-p",
        str(repo_root / "applications" / "robot_learning_workbench" / "isaac_probe.py"),
        "--mode",
        "metrics",
        "--run-dir",
        str(run_dir),
        "--output",
        str(output_path),
    )
    return CommandSpec("Read TensorBoard Metrics", argv, isaac_lab_root, output_path)


def build_experiment_script_command(
    *,
    repo_root: Path,
    isaac_lab_root: Path,
    experiment: ExperimentSummary,
    role: str,
    arguments: list[str],
) -> CommandSpec | None:
    script = experiment.scripts.get(role)
    if not script:
        return None
    return CommandSpec(
        role.replace("_", " ").title(),
        (str(isaac_lab_root / "isaaclab.bat"), "-p", str(script), *arguments),
        isaac_lab_root,
        environment={"PYTHONPATH": str(repo_root)},
    )


@dataclass
class ProcessEvent:
    kind: str
    text: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class ProcessRunner:
    """Own exactly one workbench-launched child and stream its merged output."""

    def __init__(self) -> None:
        self.events: queue.Queue[ProcessEvent] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None
        self.status = "IDLE"
        self.exit_code: int | None = None
        self.history: list[CommandSpec] = []
        self._lock = threading.Lock()
        self.on_complete: Callable[[CommandSpec, int], None] | None = None

    def start(self, spec: CommandSpec) -> None:
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                raise RuntimeError("A workbench process is already running.")
            command = self._windows_command(spec.argv)
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            environment = os.environ.copy()
            environment.update(spec.environment)
            self.process = subprocess.Popen(
                command,
                cwd=spec.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                creationflags=creation_flags,
                env=environment,
            )
            self.status = "RUNNING"
            self.exit_code = None
            self.history.append(spec)
            self.events.put(ProcessEvent("command", format_spec(spec)))
            threading.Thread(target=self._collect, args=(spec,), daemon=True).start()

    def stop(self) -> None:
        with self._lock:
            process = self.process
        if process is None or process.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T"],
                check=False,
                capture_output=True,
                timeout=10,
            )
        else:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        self.status = "STOPPED"
        self.events.put(ProcessEvent("state", "STOPPED"))

    def _collect(self, spec: CommandSpec) -> None:
        process = self.process
        assert process is not None and process.stdout is not None
        for line in process.stdout:
            self.events.put(ProcessEvent("output", line.rstrip("\r\n")))
        exit_code = process.wait()
        self.exit_code = exit_code
        if self.status != "STOPPED":
            self.status = "SUCCEEDED" if exit_code == 0 else "FAILED"
        self.events.put(ProcessEvent("exit", f"exit code {exit_code}"))
        if self.on_complete:
            self.on_complete(spec, exit_code)

    @staticmethod
    def _windows_command(argv: tuple[str, ...]) -> list[str]:
        if os.name == "nt" and argv and argv[0].lower().endswith((".bat", ".cmd")):
            return ["cmd.exe", "/d", "/s", "/c", subprocess.list2cmdline(list(argv))]
        return list(argv)
