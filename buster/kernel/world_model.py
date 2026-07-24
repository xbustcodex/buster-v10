"""
Buster Kernel - Structured World State Engine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
import platform
import psutil


@dataclass
class SystemHardwareState:
    os_name: str = platform.system()
    os_version: str = platform.version()
    cpu_count: int = psutil.cpu_count(logical=True) or 1
    ram_gb: float = round(psutil.virtual_memory().total / (1024**3), 2)
    ram_usage_pct: float = 0.0

    def refresh(self) -> None:
        self.ram_usage_pct = psutil.virtual_memory().percent


@dataclass
class WorkspaceState:
    active_project: str = "buster-v10"
    file_count: int = 0
    test_suite_status: str = "UNKNOWN"
    last_indexed: Optional[datetime] = None


class WorldModel:
    """Maintains Buster's unified awareness of system, runtime, and workspace reality."""

    def __init__(self) -> None:
        self.hardware = SystemHardwareState()
        self.workspace = WorkspaceState()
        self.active_services: Dict[str, str] = {}

    def snapshot(self) -> Dict[str, Any]:
        """Returns a consolidated JSON-serializable snapshot of Buster's reality."""
        self.hardware.refresh()
        return {
            "computer": {
                "os": f"{self.hardware.os_name} {self.hardware.os_version}",
                "cpu_cores": self.hardware.cpu_count,
                "ram_total_gb": self.hardware.ram_gb,
                "ram_used_pct": self.hardware.ram_usage_pct,
            },
            "workspace": {
                "project": self.workspace.active_project,
                "files": self.workspace.file_count,
                "test_status": self.workspace.test_suite_status,
                "last_indexed": self.workspace.last_indexed.isoformat() if self.workspace.last_indexed else None,
            },
            "runtime_services": self.active_services,
        }