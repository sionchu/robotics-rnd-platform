"""Hardware-free end-to-end Rainbow adapter, journal, and replay demo."""

from __future__ import annotations

import json
from pathlib import Path

from robotics_rnd.rb_lab import run_mock_demo


def run(journal_path: Path) -> dict[str, object]:
    return run_mock_demo(journal_path)


def main() -> int:
    print(json.dumps(run(Path("/tmp/robotics-rnd-rb-mock-demo.jsonl")), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
