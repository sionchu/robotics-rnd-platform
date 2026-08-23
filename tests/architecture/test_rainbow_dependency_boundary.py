from pathlib import Path


def test_rbpodo_import_isolated_to_optional_backend() -> None:
    source_root = Path("src/robotics_rnd")
    offenders = []
    for path in source_root.rglob("*.py"):
        if path.name == "rbpodo_backend.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "import rbpodo" in text or "from rbpodo" in text:
            offenders.append(path)
    assert offenders == []


def test_rb_cli_exposes_no_live_connection_or_motion_command() -> None:
    text = Path("src/robotics_rnd/rb.py").read_text(encoding="utf-8")
    assert "live-connect" not in text
    assert "live-move" not in text
    assert "RbpodoBackend" not in text
