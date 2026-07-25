from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class WorkspaceCleanupRunner:
    """Executes workspace maintenance tasks such as purging stale logs, temporary artifacts, and cache dirs."""

    def purge_artifacts(
        self,
        workspace_root: str | Path,
        patterns: List[str],
        max_age_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Deletes files matching specified patterns if older than max_age_seconds (if provided)."""
        root = Path(workspace_root)
        if not root.exists():
            return {"status": "failed", "error": f"Path '{workspace_root}' does not exist."}

        now = time.time()
        purged_files: List[str] = []
        bytes_freed: int = 0

        for pattern in patterns:
            for item in root.rglob(pattern):
                if not item.exists():
                    continue

                if max_age_seconds is not None:
                    mtime = item.stat().st_mtime
                    if (now - mtime) < max_age_seconds:
                        continue

                try:
                    if item.is_file() or item.is_symlink():
                        bytes_freed += item.stat().st_size
                        item.unlink()
                        purged_files.append(str(item.relative_to(root)))
                    elif item.is_dir():
                        shutil.rmtree(item)
                        purged_files.append(str(item.relative_to(root)))
                except Exception as e:
                    pass

        return {
            "status": "success",
            "purged_count": len(purged_files),
            "bytes_freed": bytes_freed,
            "purged_files": purged_files,
        }