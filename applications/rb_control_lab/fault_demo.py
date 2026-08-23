"""Demonstrate unknown command outcome and no automatic motion resume."""

from __future__ import annotations

import json

from robotics_rnd.rb_lab import run_fault_demo


def run() -> dict[str, object]:
    return run_fault_demo()


def main() -> int:
    print(json.dumps(run(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
