"""
Buster Self-Improvement Preflight Checks v1.0

Validates environmental preconditions prior to opening a PatchTransaction.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Union

logger = logging.getLogger("buster.preflight")


class PreflightCheckError(Exception):
    """Raised when environment preflight checks fail."""


class PreflightChecker:
    """Verifies environment readiness before starting patch transaction."""

    def __init__(
        self,
        project_root: Union[str, Path],
        min_disk_space_mb: int = 100,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.min_disk_space_mb = min_disk_space_mb

    def run_all(self, target_rel_path: str) -> Tuple[bool, List[str]]:
        """
        Executes preflight verification suite.
        Returns (success, list_of_failure_reasons).
        """
        failures: List[str] = []

        # 1. Disk space check
        try:
            free_space = shutil.disk_usage(self.project_root).free
            free_mb = free_space / (1024 * 1024)
            if free_mb < self.min_disk_space_mb:
                failures.append(
                    f"Insufficient disk space: {free_mb:.1f} MB available, {self.min_disk_space_mb} MB required."
                )
        except Exception as err:
            failures.append(f"Failed disk space check: {err}")

        # 2. Backup destination writability check
        backup_dir = self.project_root / "Backups"
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            test_file = backup_dir / ".write_test"
            test_file.touch(exist_ok=True)
            test_file.unlink()
        except Exception as err:
            failures.append(f"Backup directory non-writable: {err}")

        # 3. Target file existence / parent directory writability check
        target_file = (self.project_root / target_rel_path).resolve()
        if not target_file.parent.exists():
            failures.append(f"Target file directory does not exist: {target_file.parent}")
        elif not os.access(target_file.parent, os.W_OK):
            failures.append(f"Target directory non-writable: {target_file.parent}")

        # 4. Check git working tree clean (optional check)
        git_dir = self.project_root / ".git"
        if git_dir.exists():
            try:
                import subprocess
                res = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=str(self.project_root),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                # If uncommitted changes exist on the exact target file
                if any(target_rel_path in line for line in res.stdout.splitlines()):
                    failures.append(f"Uncommitted git modifications present on target file: {target_rel_path}")
            except Exception as err:
                logger.warning("Preflight Git check skipped: %s", err)

        return (len(failures) == 0, failures)