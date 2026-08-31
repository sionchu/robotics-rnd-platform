"""Safe repository, experiment, environment, GPU, and run discovery."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import Any

from .models import ExperimentSummary, WorkspaceState

EXPERIMENT_PATTERN = re.compile(r"^(?P<number>\d{3})_(?P<name>.+)$")
SCRIPT_NAMES = {
    "prekit": "prekit_check.py",
    "gui": "gui_probe.py",
    "semantic": "semantic_probe.py",
    "random": "random_baseline.py",
    "evaluate": "evaluate.py",
}


def discover_experiments(repo_root: Path) -> list[ExperimentSummary]:
    """Find registered robot experiments through source parsing only."""

    root = repo_root / "experiments" / "robot"
    if not root.is_dir():
        return []
    discovered: list[ExperimentSummary] = []
    for folder in sorted(root.iterdir()):
        match = EXPERIMENT_PATTERN.match(folder.name)
        registration = folder / "registration.py"
        if not match or not registration.is_file():
            continue
        metadata = parse_registration(registration)
        module = ".".join(registration.relative_to(repo_root).with_suffix("").parts)
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


def inspect_workspace(repo_root: Path, isaac_lab_root: Path | None) -> WorkspaceState:
    status_lines = _git(repo_root, "status", "--porcelain").splitlines()
    branch = _git(repo_root, "branch", "--show-current") or "DETACHED"
    head = _git(repo_root, "rev-parse", "HEAD")
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
        repo_root=repo_root,
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


def find_repo_root(start: Path) -> Path | None:
    output = _git(start, "rev-parse", "--show-toplevel")
    return Path(output) if output else None


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
