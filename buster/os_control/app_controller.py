# buster/os_control/app_controller.py
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class WindowsAppController:
    """Enables Buster to launch applications, open web URLs freely, and manage software execution."""

    def launch_app(self, app_path_or_command: str, arguments: Optional[str] = None) -> bool:
        """Launches any application, executable, or system utility on Windows."""
        full_cmd = f'start "" "{app_path_or_command}"'
        if arguments:
            full_cmd = f'start "" "{app_path_or_command}" {arguments}'

        logger.info(f"Launching application: {full_cmd}")
        try:
            subprocess.run(["cmd.exe", "/c", full_cmd], check=True, timeout=10)
            return True
        except Exception as e:
            logger.error(f"Failed to launch app [{app_path_or_command}]: {e}")
            return False

    def open_web_url(self, url: str) -> bool:
        """Freely opens any web page or URL in the default browser."""
        logger.info(f"Opening web URL: {url}")
        return self.launch_app(url)

    def terminate_process_by_name(self, process_name: str) -> bool:
        """Terminates an application or process by its image name (e.g., 'notepad.exe')."""
        cmd = f"taskkill /f /im {process_name}"
        logger.info(f"Terminating process: {cmd}")
        try:
            res = subprocess.run(["cmd.exe", "/c", cmd], capture_output=True, text=True, timeout=10)
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to terminate process [{process_name}]: {e}")
            return False