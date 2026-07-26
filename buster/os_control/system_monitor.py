# buster/os_control/system_monitor.py
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    active_processes_count: int


class WindowsSystemMonitor:
    """Monitors hardware metrics and manages Windows network radios (Wi-Fi, Bluetooth)."""

    def get_metrics(self) -> SystemMetrics:
        """Collects real-time CPU, RAM, disk, and process telemetry."""
        return SystemMetrics(
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_percent=psutil.virtual_memory().percent,
            disk_percent=psutil.disk_usage("C:\\").percent,
            active_processes_count=len(psutil.pids()),
        )

    def control_wifi(self, enable: bool) -> bool:
        """Enables or disables Windows Wi-Fi adapter via netsh."""
        state_str = "enabled" if enable else "disabled"
        cmd = f'netsh interface set interface "Wi-Fi" admin={state_str}'
        logger.info(f"Executing Wi-Fi toggle: {cmd}")
        try:
            res = subprocess.run(["cmd.exe", "/c", cmd], capture_output=True, text=True, timeout=10)
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to control Wi-Fi: {e}")
            return False

    def list_running_apps(self) -> List[Dict[str, Any]]:
        """Lists high-level active processes running on Windows."""
        apps = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                apps.append({
                    "pid": p.info['pid'],
                    "name": p.info['name'],
                    "cpu_percent": p.info['cpu_percent'],
                    "memory_percent": p.info['memory_percent'],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return apps