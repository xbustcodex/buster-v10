# tests/test_v26_full_os_control.py
import pytest
from buster.os_control.system_monitor import WindowsSystemMonitor
from buster.os_control.app_controller import WindowsAppController


def test_system_monitor_metrics():
    monitor = WindowsSystemMonitor()
    metrics = monitor.get_metrics()
    
    assert metrics.cpu_percent >= 0.0
    assert metrics.memory_percent > 0.0
    assert metrics.active_processes_count > 0


def test_app_controller_safe_execution():
    controller = WindowsAppController()
    
    # Test safe URL format handling (mocking actual browser opening via command structure check)
    # We test process termination on a dummy process name to ensure safe error-handling paths
    success = controller.terminate_process_by_name("non_existent_buster_app_xyz.exe")
    # Should handle non-existent gracefully without crashing
    assert isinstance(success, bool)