from pathlib import Path

from scripts.doctor import nvidia_driver_status, nvidia_hardware


def write_gpu_fixture(root: Path) -> tuple[Path, Path]:
    proc_root = root / "proc" / "0000:04:00.0"
    proc_root.mkdir(parents=True)
    (proc_root / "information").write_text(
        "Model: NVIDIA Test GPU\n"
        "GPU UUID: GPU-private-value-must-not-leak\n"
        "Bus Location: 0000:04:00.0\n",
        encoding="utf-8",
    )
    pci_root = root / "pci"
    device = pci_root / "0000:04:00.0"
    (device / "power").mkdir(parents=True)
    (device / "power" / "runtime_status").write_text("active\n", encoding="utf-8")
    driver = root / "drivers" / "nvidia"
    driver.mkdir(parents=True)
    (device / "driver").symlink_to(driver, target_is_directory=True)
    return proc_root.parent, pci_root


def test_nvidia_hardware_reports_safe_evidence_without_uuid(tmp_path: Path) -> None:
    proc_root, pci_root = write_gpu_fixture(tmp_path)
    result = nvidia_hardware(proc_root, pci_root)

    assert result["status"] == "detected"
    assert result["devices"] == [
        {
            "model": "NVIDIA Test GPU",
            "pci_address": "0000:04:00.0",
            "kernel_driver": "nvidia",
            "runtime_power": "active",
        }
    ]
    assert "UUID" not in str(result)
    assert "private-value" not in str(result)


def test_driver_usable_requires_binding_and_character_devices(tmp_path: Path) -> None:
    proc_root, pci_root = write_gpu_fixture(tmp_path)
    hardware = nvidia_hardware(proc_root, pci_root)
    dev_root = tmp_path / "dev"
    dev_root.mkdir()

    missing = nvidia_driver_status(hardware, dev_root)
    assert missing["status"] == "unusable"
    assert missing["kernel_bound"] is True
    assert "character devices are unavailable" in missing["detail"]

    (dev_root / "nvidiactl").touch()
    (dev_root / "nvidia0").touch()
    available = nvidia_driver_status(hardware, dev_root)
    assert available["status"] == "usable"
    assert available["gpu_nodes"] == ["nvidia0"]


def test_no_gpu_is_distinct_from_unusable_driver(tmp_path: Path) -> None:
    hardware = nvidia_hardware(tmp_path / "missing-proc", tmp_path / "missing-pci")
    status = nvidia_driver_status(hardware, tmp_path / "dev")

    assert hardware == {"status": "missing", "devices": []}
    assert status["status"] == "unusable"
    assert status["kernel_bound"] is False
    assert "No NVIDIA display hardware" in status["detail"]
