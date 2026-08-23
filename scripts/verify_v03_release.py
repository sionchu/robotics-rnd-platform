"""Verify software-only v0.3 release evidence without contacting hardware."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from robotics_rnd import __version__

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "THIRD_PARTY.md",
    "docs/research/EXTERNAL_RESEARCH_INTAKE.md",
    "docs/research/TECHNOLOGY_DECISIONS.md",
    "docs/research/RBPODO_EVALUATION.md",
    "docs/research/RBPODO_INTEGRATION_RISKS.md",
    "docs/research/RB_COMPATIBILITY_MATRIX.md",
    "docs/research/RB_HARDWARE_VALIDATION_LEVELS.md",
    "docs/research/RB_HARDWARE_HANDOFF.md",
    "docs/architecture/ROBOT_CONTROL_SAFETY_BOUNDARY.md",
    "docs/architecture/RB_APPLICATION_REBUILD.md",
    "docs/releases/v0.3.0.md",
    "research/registry/repositories.yaml",
    "research/registry/libraries.yaml",
    "research/registry/papers.yaml",
    "research/registry/algorithms.yaml",
    "research/registry/vendors.yaml",
    "research/registry/datasets.yaml",
)
EXPERIMENTS = (
    "013_rb_pose_mapping",
    "014_rbpodo_command_semantics",
    "015_rb_fault_reconnect",
    "016_rb_io_contract",
)


def verify() -> dict[str, object]:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise RuntimeError(f"missing v0.3 release artifacts: {missing}")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if project["project"]["version"] != "0.3.0" or __version__ != "0.3.0":
        raise RuntimeError("package and module versions must both be 0.3.0")
    for experiment in EXPERIMENTS:
        root = ROOT / "experiments/robot" / experiment
        for artifact in ("README.md", "conclusion.md", "config/config.json", "results/metrics.json"):
            if not (root / artifact).is_file():
                raise RuntimeError(f"{experiment} is missing {artifact}")
        metrics = json.loads((root / "results/metrics.json").read_text(encoding="utf-8"))
        if metrics.get("decision") != "PROMOTE_TO_PLATFORM":
            raise RuntimeError(f"{experiment} lacks an explicit promotion decision")
        if metrics.get("hardware_validation") is not False:
            raise RuntimeError(f"{experiment} contains an invalid hardware claim")
        if metrics.get("max_hardware_validation_level") != 0:
            raise RuntimeError(f"{experiment} exceeds hardware validation LEVEL 0")
        if not all(metrics.get("acceptance", {}).values()):
            raise RuntimeError(f"{experiment} acceptance gate failed")
    release = (ROOT / "docs/releases/v0.3.0.md").read_text(encoding="utf-8")
    for label in (
        "SOFTWARE_VALIDATED",
        "HARDWARE_NOT_VALIDATED",
        "hardware_validation: false",
        "max_hardware_validation_level: 0",
        "v0.3.0-rb-control-lab",
    ):
        if label not in release:
            raise RuntimeError(f"release documentation is missing {label}")
    cli = (ROOT / "src/robotics_rnd/rb.py").read_text(encoding="utf-8")
    if "RbpodoBackend" in cli or "live-connect" in cli or "live-move" in cli:
        raise RuntimeError("RB CLI contains a forbidden live backend/motion path")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    if ".external/" not in gitignore or "robot_sessions/local/**" not in gitignore:
        raise RuntimeError("external intake or local robot sessions are not ignored")
    return {
        "status": "SOFTWARE_VALIDATED",
        "hardware_status": "HARDWARE_NOT_VALIDATED",
        "hardware_validation": False,
        "max_hardware_validation_level": 0,
        "experiments_verified": len(EXPERIMENTS),
        "release_artifacts_verified": len(REQUIRED),
    }


def main() -> int:
    print(json.dumps(verify(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
