"""Inspect a portable robot journal without opening a controller connection."""

from __future__ import annotations

import json
from pathlib import Path

from robotics_rnd.rb_lab import run_replay_demo


def run(journal_path: Path) -> dict[str, object]:
    return run_replay_demo(journal_path)


def main(path: str = "/tmp/robotics-rnd-rb-mock-demo.jsonl") -> int:
    print(json.dumps(run(Path(path)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
