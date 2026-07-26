# tests/test_v28_daemon.py
import pytest
from buster.daemon.service_manager import BusterDaemonManager


def test_daemon_guarded_loop_success():
    manager = BusterDaemonManager(service_name="TestBusterDaemon")

    counter = {"runs": 0}
    def sample_task():
        counter["runs"] += 1

    status = manager.run_guarded_loop(sample_task, max_iterations=3)

    assert status.is_running is True
    assert status.restart_count == 0
    assert counter["runs"] == 3


def test_daemon_crash_recovery_and_retry():
    manager = BusterDaemonManager(service_name="CrashBusterDaemon", max_retries=3)

    def crashing_task():
        raise RuntimeError("Simulated background fault")

    status = manager.run_guarded_loop(crashing_task, max_iterations=1)

    # Should attempt until max retries is reached and halt
    assert status.is_running is False
    assert status.restart_count == 3


def test_winsw_config_generation(tmp_path):
    manager = BusterDaemonManager()
    xml_file = tmp_path / "buster_service.xml"

    path = manager.generate_winsw_xml_config(
        python_executable_path="C:\\Python312\\python.exe",
        script_path="C:\\buster\\main.py",
        output_path=xml_file,
    )

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "BusterAutonomousService" in content
    assert "C:\\Python312\\python.exe" in content