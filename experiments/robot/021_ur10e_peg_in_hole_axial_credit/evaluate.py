"""Reuse the finite Experiment 020 evaluator for the Experiment 021 task."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path


def _output_path() -> Path | None:
    try:
        return Path(sys.argv[sys.argv.index("--output") + 1])
    except (ValueError, IndexError):
        return None


def main() -> int:
    registration = importlib.import_module(
        "experiments.robot.021_ur10e_peg_in_hole_axial_credit.registration"
    )
    registration.register_tasks()
    evaluator = Path(__file__).parents[1] / "020_ur10e_peg_in_hole_state_precision" / "evaluate.py"
    bootstrap = (
        "import importlib, runpy, sys; "
        "evaluator_path=sys.argv[1]; evaluator_args=sys.argv[2:]; "
        "importlib.import_module("
        "'experiments.robot.021_ur10e_peg_in_hole_axial_credit.registration'"
        ").register_tasks(); "
        "sys.argv=[evaluator_path, *evaluator_args]; "
        "runpy.run_path(evaluator_path, run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-c", bootstrap, str(evaluator), *sys.argv[1:]],
        check=False,
    )
    if result.returncode != 0:
        return result.returncode
    output = _output_path()
    if output is not None and output.is_file():
        document = json.loads(output.read_text(encoding="utf-8"))
        document["experiment"] = "021"
        document["evaluation_wrapper"] = str(evaluator)
        document["task_reward_term"] = "gated_axial_progress"
        output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
