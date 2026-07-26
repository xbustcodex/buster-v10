# buster/daemon/service_manager.py
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class DaemonStatus:
    is_running: bool
    restart_count: int
    last_heartbeat: str
    uptime_seconds: float


class BusterDaemonManager:
    """Manages background daemonization, crash recovery, and auto-restart loops for Buster."""

    def __init__(self, service_name: str = "BusterAutonomousService", max_retries: int = 3) -> None:
        self.service_name = service_name
        self.max_retries = max_retries
        self.restart_count = 0
        self.is_running = False
        self.start_time: Optional[float] = None

    def run_guarded_loop(self, task_callback: Callable[[], None], max_iterations: int = 1) -> DaemonStatus:
        """Runs a protected task loop with automatic crash recovery and restart tracking."""
        self.is_running = True
        self.start_time = time.time()
        success_count = 0

        while self.is_running and success_count < max_iterations:
            try:
                logger.info(f"Daemon [{self.service_name}] executing iteration {success_count + 1}")
                task_callback()
                success_count += 1
            except Exception as e:
                self.restart_count += 1
                logger.error(f"Daemon crashed with error: {e}. Restart attempt {self.restart_count}/{self.max_retries}")
                if self.restart_count >= self.max_retries:
                    logger.critical("Max restart retries exceeded. Stopping daemon guard.")
                    self.is_running = False
                    break
                time.sleep(0.01)

        uptime = time.time() - (self.start_time or time.time())
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        
        return DaemonStatus(
            is_running=self.is_running,
            restart_count=self.restart_count,
            last_heartbeat=now_iso,
            uptime_seconds=uptime,
        )

    def generate_winsw_xml_config(self, python_executable_path: str, script_path: str, output_path: str | Path = "buster_service.xml") -> Path:
        """Generates a Windows Service Wrapper (WinSW) XML configuration for native OS background service registration."""
        xml_content = f"""<service>
  <id>{self.service_name}</id>
  <name>Buster Autonomous AI Service</name>
  <description>Provides autonomous background execution, system monitoring, and mesh sync for Buster AI.</description>
  <executable>{python_executable_path}</executable>
  <arguments>"{script_path}"</arguments>
  <log mode="roll-by-size">
    <sizeThreshold>10240</sizeThreshold>
    <keepFiles>8</keepFiles>
  </log>
  <onfailure action="restart" delay="10sec"/>
  <serviceaccount>
    <account></account>
    <password></password>
  </serviceaccount>
  <workingdirectory>.</workingdirectory>
</service>
"""
        target = Path(output_path)
        target.write_text(xml_content, encoding="utf-8")
        logger.info(f"Generated Windows Service Wrapper configuration at: {target}")
        return target