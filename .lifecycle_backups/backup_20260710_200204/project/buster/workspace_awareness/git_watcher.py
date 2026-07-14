from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import subprocess

from .workspace_events import WorkspaceEvent


class GitWatcher:
    def detect_path(self, path: str | Path) -> List[WorkspaceEvent]:
        root = Path(path)
        if not (root / ".git").exists():
            return []

        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = [line for line in result.stdout.splitlines() if line.strip()]
        except Exception:
            lines = []

        if not lines:
            return [
                WorkspaceEvent(
                    type="git.clean",
                    summary="Git workspace is clean",
                    confidence=0.8,
                    importance=0.3,
                    data={"path": str(root), "changes": 0},
                )
            ]

        return [
            WorkspaceEvent(
                type="git.changed",
                summary=f"Git workspace has {len(lines)} changed file(s)",
                confidence=0.9,
                importance=0.75,
                data={"path": str(root), "changes": len(lines), "files": lines[:20]},
            )
        ]

    def detect(self, context: Dict[str, Any]) -> List[WorkspaceEvent]:
        path = context.get("project_path") or context.get("cwd")
        if not path:
            return []
        return self.detect_path(path)
