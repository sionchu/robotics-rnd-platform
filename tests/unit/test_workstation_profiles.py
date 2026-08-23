from __future__ import annotations

import tomllib
from pathlib import Path


def test_example_workstation_profiles_have_required_boundaries() -> None:
    profiles = sorted(Path("config/workstations").glob("*.example.toml"))
    assert {path.name for path in profiles} == {
        "ubuntu-laptop.example.toml",
        "windows-desktop.example.toml",
        "wsl2.example.toml",
    }

    for path in profiles:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        assert document["profile_name"]
        assert document["role"]
        assert document["data"]["root"]
        assert document["models"]["root"]
        assert document["usd"]["root"]
        assert isinstance(document["capabilities"]["real_robot"], bool)
