"""Safe repository, experiment, environment, GPU, and run discovery."""

from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .models import ExperimentSummary, WorkspaceState

EXPERIMENT_PATTERN = re.compile(r"^(?P<number>\d{3})_(?P<name>.+)$")
WORKSPACE_MANIFEST = "robot_learning_workbench_tasks.json"
SCRIPT_NAMES = {
    "prekit": "prekit_check.py",
    "gui": "gui_probe.py",
    "semantic": "semantic_probe.py",
    "random": "random_baseline.py",
    "evaluate": "evaluate.py",
}


def discover_tasks(workspace_root: Path) -> list[ExperimentSummary]:
    """Discover trusted workspace task metadata without importing task code.

    A standalone workspace may declare registrations in
    ``robot_learning_workbench_tasks.json``.  The legacy robotics-rnd
    ``experiments/robot/<number>_<name>/registration.py`` layout remains a
    workspace-local discovery adapter, not a Workbench requirement.
    """

    discovered = _discover_manifest_tasks(workspace_root)
    discovered.extend(_discover_legacy_robot_experiments(workspace_root))
    unique = {item.registration_path.resolve(): item for item in discovered}
    return sorted(unique.values(), key=lambda item: (item.number, item.name, str(item.path)))


def _discover_legacy_robot_experiments(workspace_root: Path) -> list[ExperimentSummary]:
    """Support the existing robotics-rnd experiment layout when present."""

    root = workspace_root / "experiments" / "robot"
    if not root.is_dir():
        return []
    discovered: list[ExperimentSummary] = []
    for folder in sorted(root.iterdir()):
        match = EXPERIMENT_PATTERN.match(folder.name)
        registration = folder / "registration.py"
        if not match or not registration.is_file():
            continue
        metadata = parse_registration(registration)
        module = _module_name(workspace_root, registration)
        scripts = {
            role: candidate
            for role, filename in SCRIPT_NAMES.items()
            if (candidate := folder / filename).is_file()
        }
        discovered.append(
            ExperimentSummary(
                number=int(match.group("number")),
                name=match.group("name").replace("_", " "),
                path=folder,
                registration_path=registration,
                registration_module=module,
                task_id=_string(metadata.get("TASK_ID")),
                play_task_id=_string(metadata.get("PLAY_TASK_ID")),
                runtime_module=_string(metadata.get("RUNTIME_MODULE")),
                env_config_class=_string(metadata.get("env_config_class")),
                play_config_class=_string(metadata.get("play_config_class")),
                ppo_config_class=_string(metadata.get("ppo_config_class")),
                scripts=scripts,
            )
        )
    return discovered


def _discover_manifest_tasks(workspace_root: Path) -> list[ExperimentSummary]:
    manifest = workspace_root / WORKSPACE_MANIFEST
    if not manifest.is_file():
        return []
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    entries = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return []
    discovered: list[ExperimentSummary] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or not isinstance(entry.get("registration"), str):
            continue
        registration = _workspace_file(workspace_root, entry["registration"])
        if registration is None or not registration.is_file() or registration.suffix != ".py":
            continue
        metadata = parse_registration(registration)
        command_paths = entry.get("commands")
        scripts = (
            {
                role: path
                for role, relative in command_paths.items()
                if role in SCRIPT_NAMES
                and isinstance(relative, str)
                and (path := _workspace_file(workspace_root, relative)) is not None
                and path.is_file()
            }
            if isinstance(command_paths, dict)
            else {}
        )
        number = entry.get("number")
        discovered.append(
            ExperimentSummary(
                number=number if isinstance(number, int) and not isinstance(number, bool) else index,
                name=str(entry.get("name") or registration.parent.name.replace("_", " ")),
                path=registration.parent,
                registration_path=registration,
                registration_module=_module_name(workspace_root, registration),
                task_id=_string(metadata.get("TASK_ID")),
                play_task_id=_string(metadata.get("PLAY_TASK_ID")),
                runtime_module=_string(metadata.get("RUNTIME_MODULE")),
                env_config_class=_string(metadata.get("env_config_class")),
                play_config_class=_string(metadata.get("play_config_class")),
                ppo_config_class=_string(metadata.get("ppo_config_class")),
                scripts=scripts,
            )
        )
    return discovered


def parse_registration(path: Path) -> dict[str, Any]:
    """Read task IDs and class ownership without executing source."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value_node = node.value
            for target in targets:
                if isinstance(target, ast.Name) and target.id in {
                    "TASK_ID",
                    "PLAY_TASK_ID",
                    "RUNTIME_MODULE",
                }:
                    value = _literal(value_node)
                    if value is not None:
                        result[target.id] = value
        if isinstance(node, ast.ClassDef):
            if node.name.endswith("EnvCfg_PLAY"):
                result["play_config_class"] = node.name
            elif node.name.endswith("EnvCfg"):
                result["env_config_class"] = node.name
            elif node.name.endswith("PPORunnerCfg"):
                result["ppo_config_class"] = node.name
    return result


def inspect_workspace(workspace_root: Path, isaac_lab_root: Path | None) -> WorkspaceState:
    status_lines = _git(workspace_root, "status", "--porcelain").splitlines()
    branch = _git(workspace_root, "branch", "--show-current") or "DETACHED"
    head = _git(workspace_root, "rev-parse", "HEAD")
    tracked_dirty = any(not line.startswith("??") for line in status_lines)
    untracked_count = sum(line.startswith("??") for line in status_lines)
    isaac_commit = None
    isaac_sim_path = None
    if isaac_lab_root and isaac_lab_root.is_dir():
        isaac_commit = _git(isaac_lab_root, "rev-parse", "HEAD") or None
        link = isaac_lab_root / "_isaac_sim"
        if link.exists():
            try:
                isaac_sim_path = link.resolve(strict=True)
            except OSError:
                isaac_sim_path = None
    return WorkspaceState(
        workspace_root=workspace_root,
        branch=branch,
        head=head,
        tracked_dirty=tracked_dirty,
        untracked_count=untracked_count,
        isaac_lab_root=isaac_lab_root if isaac_lab_root and isaac_lab_root.is_dir() else None,
        isaac_lab_commit=isaac_commit,
        isaac_sim_path=isaac_sim_path,
        gpu=detect_gpu(),
        latest_run_dir=find_latest_run(isaac_lab_root),
    )


def detect_gpu() -> str | None:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip().splitlines()[0] if result.returncode == 0 and result.stdout.strip() else None


def find_latest_run(isaac_lab_root: Path | None) -> Path | None:
    if not isaac_lab_root:
        return None
    logs = isaac_lab_root / "logs" / "rsl_rl"
    if not logs.is_dir():
        return None
    candidates = [path for path in logs.glob("*/*") if path.is_dir()]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def workbench_root() -> Path:
    """Return the source/install root that owns the Workbench helper."""

    return Path(__file__).resolve().parents[2]


def _module_name(workspace_root: Path, registration: Path) -> str:
    return ".".join(registration.relative_to(workspace_root).with_suffix("").parts)


def _workspace_file(workspace_root: Path, relative: str) -> Path | None:
    root = workspace_root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _git(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args], check=False, cwd=cwd, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _literal(node: ast.AST | None) -> Any:
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return None


def _string(value: Any) -> str | None:
    return str(value) if isinstance(value, str) else None
