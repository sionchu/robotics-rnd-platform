"""Small UI-facing models and pure transformations for the workbench."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

APP_DIR_NAME = "robot-learning-workbench"


@dataclass(frozen=True)
class ExperimentSummary:
    """Experiment metadata obtained without importing experiment modules."""

    number: int
    name: str
    path: Path
    registration_path: Path
    registration_module: str
    task_id: str | None = None
    play_task_id: str | None = None
    runtime_module: str | None = None
    env_config_class: str | None = None
    play_config_class: str | None = None
    ppo_config_class: str | None = None
    scripts: dict[str, Path] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkspaceState:
    repo_root: Path
    branch: str
    head: str
    tracked_dirty: bool
    untracked_count: int
    isaac_lab_root: Path | None
    isaac_lab_commit: str | None
    isaac_sim_path: Path | None
    gpu: str | None
    latest_run_dir: Path | None


@dataclass(frozen=True)
class CommandSpec:
    label: str
    argv: tuple[str, ...]
    cwd: Path
    output_path: Path | None = None
    environment: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    name: str
    points: list[tuple[int, float]] = field(default_factory=list)

    @classmethod
    def from_json(cls, name: str, values: Any) -> MetricSeries:
        points: list[tuple[int, float]] = []
        if isinstance(values, list):
            for index, value in enumerate(values):
                if isinstance(value, dict) and "value" in value:
                    points.append((int(value.get("step", index)), float(value["value"])))
                elif isinstance(value, int | float):
                    points.append((index, float(value)))
        return cls(name=name, points=points)

    def first_last(self) -> tuple[float | None, float | None]:
        if not self.points:
            return None, None
        return self.points[0][1], self.points[-1][1]


@dataclass
class EvaluationResult:
    source_path: Path
    label: str
    task: str | None
    checkpoint_sha256: str | None
    episodes: int | None
    successes: int | None
    timeouts: int | None
    metrics: dict[str, float | int | str | None]
    regions: dict[str, dict[str, Any]]
    taxonomy: dict[str, int]
    episode_records: dict[str, dict[str, Any]]
    raw: dict[str, Any]


@dataclass
class WorkbenchSettings:
    repo_root: str = ""
    isaac_lab_root: str = ""
    selected_experiment: str = ""
    selected_task: str = ""
    presentation_mode: str = "guided"
    window_geometry: str = "1480x900"
    gui_reviewed: dict[str, bool] = field(default_factory=dict)
    asset_catalog: list[dict[str, str]] = field(default_factory=list)
    experiment_notes: dict[str, dict[str, str]] = field(default_factory=dict)
    recent_evidence: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | None = None) -> WorkbenchSettings:
        settings_file = path or settings_path()
        if not settings_file.is_file():
            return cls()
        try:
            payload = json.loads(settings_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in payload.items() if key in allowed})

    def save(self, path: Path | None = None) -> Path:
        settings_file = path or settings_path()
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = settings_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, settings_file)
        return settings_file


def settings_path() -> Path:
    """Return the untracked, per-user settings location."""

    local = os.environ.get("LOCALAPPDATA")
    base = Path(local) if local else Path.home() / "AppData" / "Local"
    return base / "robotics-rnd-platform" / APP_DIR_NAME / "settings.json"


def session_path(name: str) -> Path:
    base = settings_path().parent
    base.mkdir(parents=True, exist_ok=True)
    return base / name


def normalized_to_physical(action: list[float] | tuple[float, ...], scale_m: float) -> list[float]:
    """Convert normalized relative-position actions to physical metres."""

    return [float(value) * scale_m for value in action]


def observation_term_rows(observation_groups: Any) -> list[tuple[str, str, str, str]]:
    """Render canonical observation records without reconstructing runtime semantics."""

    if not isinstance(observation_groups, list):
        return []
    rows: list[tuple[str, str, str, str]] = []
    for group in observation_groups:
        if not isinstance(group, dict):
            continue
        terms = group.get("terms")
        if not isinstance(terms, list):
            continue
        for term in terms:
            if not isinstance(term, dict):
                continue
            dimension = term.get("dimension")
            dimension_text = (
                str(dimension)
                if isinstance(dimension, int) and not isinstance(dimension, bool)
                else "N/A — runtime probe required"
            )
            rows.append(
                (
                    str(term.get("name") or "unnamed"),
                    f"dim={dimension_text}; {term.get('meaning') or ''}",
                    str(term.get("unit") or ""),
                    str(term.get("dimension_source") or term.get("source") or "Task Config"),
                )
            )
    return rows


def observation_dimension_consistency(
    observation_groups: Any, group_name: str, runtime_total: Any
) -> str | None:
    """Return a clear diagnostic when complete term dimensions disagree with runtime total."""

    if not isinstance(observation_groups, list):
        return None
    if not isinstance(runtime_total, int) or isinstance(runtime_total, bool):
        return None
    group = next(
        (item for item in observation_groups if isinstance(item, dict) and item.get("group") == group_name),
        None,
    )
    if group is None or not isinstance(group.get("terms"), list):
        return None
    dimensions = [term.get("dimension") for term in group["terms"] if isinstance(term, dict)]
    integer_dimensions = [
        int(value) for value in dimensions if isinstance(value, int) and not isinstance(value, bool)
    ]
    if not dimensions or len(integer_dimensions) != len(dimensions):
        return None
    term_total = sum(integer_dimensions)
    if term_total == runtime_total:
        return None
    return f"MISMATCH: observation term sum {term_total} does not equal runtime policy total {runtime_total}."


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Calculate a checkpoint hash without loading the whole artifact into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_last_jsonl_record(path: Path, *, max_bytes: int = 64 * 1024) -> dict[str, Any] | None:
    """Read the latest complete JSON object from a bounded tail of a telemetry file."""

    try:
        with path.open("rb") as stream:
            size = stream.seek(0, os.SEEK_END)
            start = max(size - max_bytes, 0)
            stream.seek(start)
            data = stream.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    lines = data.splitlines()
    if start and lines:
        lines = lines[1:]
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def explain_reward_gate(
    *,
    reward_name: str,
    xy_error_m: float | None,
    gate_threshold_m: float | None,
    raw_value: float | None = None,
) -> str:
    """Explain one explicit lateral reward gate without causal speculation."""

    if xy_error_m is None or gate_threshold_m is None:
        return "Gate metadata or live XY state is unavailable."
    xy_mm = xy_error_m * 1000.0
    gate_mm = gate_threshold_m * 1000.0
    if xy_error_m > gate_threshold_m:
        return f"{reward_name} = 0 because XY error {xy_mm:.2f} mm is outside the {gate_mm:.2f} mm gate."
    if raw_value is None:
        return f"{reward_name} gate is ON because XY error {xy_mm:.2f} mm is within {gate_mm:.2f} mm."
    return f"{reward_name} gate is ON at XY error {xy_mm:.2f} mm; the measured raw value is {raw_value:+.6f}."


def normalize_evaluation(path: Path) -> EvaluationResult:
    """Normalize known evidence JSON while retaining task-specific raw fields."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    records_raw = raw.get("paired_episode_records") or raw.get("episode_records") or []
    records = {
        str(record.get("episode_id")): record
        for record in records_raw
        if isinstance(record, dict) and record.get("episode_id") is not None
    }
    taxonomy_raw = raw.get("failure_taxonomy") or raw.get("failure_categories") or {}
    if not taxonomy_raw and isinstance(raw.get("standard_failure_categories"), dict):
        taxonomy_raw = raw["standard_failure_categories"]
    metrics: dict[str, float | int | str | None] = {}
    metric_keys = (
        "success_rate",
        "mean_final_xy_error_mm",
        "median_final_xy_error_mm",
        "mean_max_insertion_depth_mm",
        "median_max_insertion_depth_mm",
        "mean_episode_length",
        "mean_episodic_reward",
        "mean_max_contact_force_n",
        "max_contact_force_n",
    )
    for key in metric_keys:
        if key not in raw:
            continue
        value = raw[key]
        if isinstance(value, int | float | str) or value is None:
            metrics[key] = value
    episodes = _optional_int(raw.get("episodes") or raw.get("completed_episodes"))
    successes = _optional_int(raw.get("successes"))
    timeouts = _optional_int(raw.get("timeouts"))
    label = str(raw.get("run_name") or raw.get("experiment") or path.stem)
    return EvaluationResult(
        source_path=path,
        label=label,
        task=_optional_str(raw.get("task")),
        checkpoint_sha256=_optional_str(raw.get("checkpoint_sha256")),
        episodes=episodes,
        successes=successes,
        timeouts=timeouts,
        metrics=metrics,
        regions=raw.get("regions") if isinstance(raw.get("regions"), dict) else {},
        taxonomy={str(key): int(value) for key, value in taxonomy_raw.items()},
        episode_records=records,
        raw=raw,
    )


def transition_matrix(first: EvaluationResult, second: EvaluationResult) -> dict[str, int]:
    """Compare policy outcomes on exactly shared stable episode IDs."""

    shared = sorted(set(first.episode_records) & set(second.episode_records))
    result = {
        "A SUCCESS -> B SUCCESS": 0,
        "A SUCCESS -> B FAILURE": 0,
        "A FAILURE -> B SUCCESS": 0,
        "A FAILURE -> B FAILURE": 0,
    }
    for episode_id in shared:
        first_success = bool(first.episode_records[episode_id].get("success"))
        second_success = bool(second.episode_records[episode_id].get("success"))
        left = "SUCCESS" if first_success else "FAILURE"
        right = "SUCCESS" if second_success else "FAILURE"
        result[f"A {left} -> B {right}"] += 1
    return result


def measured_change(series: dict[str, MetricSeries]) -> list[str]:
    """Create conservative statements from measured endpoints only."""

    statements: list[str] = []
    success = series.get("Episode_Termination/success")
    if success and success.points and all(value == 0.0 for _, value in success.points):
        statements.append("Success has remained 0 for the loaded interval.")
    for key, label in (
        ("Policy/mean_std", "Policy std"),
        ("Train/mean_reward", "Mean reward"),
        ("Train/mean_episode_length", "Episode length"),
    ):
        metric = series.get(key)
        if metric:
            first, last = metric.first_last()
            if first is not None and last is not None:
                statements.append(f"{label} changed from {first:.4g} to {last:.4g}.")
    axial = next((value for key, value in series.items() if "axial" in key.lower()), None)
    if axial and any(value != 0.0 for _, value in axial.points):
        statements.append("An axial reward metric is non-zero in the loaded interval.")
    return statements


def _optional_int(value: Any) -> int | None:
    return int(value) if isinstance(value, int | float) else None


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
