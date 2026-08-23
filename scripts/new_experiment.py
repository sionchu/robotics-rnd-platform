#!/usr/bin/env python3
"""Create a dated experiment from the tracked template."""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import date
from pathlib import Path


def slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not result:
        raise ValueError("experiment name must contain a letter or number")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", help="short experiment name")
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD prefix")
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[1]
    source = project_root / "experiments" / "_template"
    destination = project_root / "experiments" / f"{args.date}-{slug(args.name)}"
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copytree(source, destination)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
