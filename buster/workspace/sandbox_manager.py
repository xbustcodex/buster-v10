from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


class SandboxManager:
    def __init__(self, root_dir: str | Path = "."):
        self.root_dir = Path(root_dir).resolve()
        self.sandbox_base = self.root_dir / ".buster_sandboxes"
        self.sandbox_base.mkdir(parents=True, exist_ok=True)
        self.active_sandboxes: Dict[str, Path] = {}

    def create_sandbox(self, prefix: str = "sandbox") -> str:
        sandbox_id = f"{prefix}_{uuid.uuid4().hex[:8]}"
        sandbox_path = self.sandbox_base / sandbox_id
        sandbox_path.mkdir(parents=True, exist_ok=True)
        self.active_sandboxes[sandbox_id] = sandbox_path
        return sandbox_id

    def clone_workspace_to_sandbox(
        self, sandbox_id: str, ignore_patterns: Optional[list] = None
    ) -> Path:
        if sandbox_id not in self.active_sandboxes:
            raise KeyError(f"Sandbox ID {sandbox_id} not recognized.")

        target_dir = self.active_sandboxes[sandbox_id]
        ignore = shutil.ignore_patterns(
            *(ignore_patterns or [".git", "__pycache__", ".buster_sandboxes", "venv"])
        )

        for item in self.root_dir.iterdir():
            if item.name.startswith(".buster_sandboxes") or item.name == ".git":
                continue
            dest = target_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, ignore=ignore, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        return target_dir

    def cleanup_sandbox(self, sandbox_id: str) -> bool:
        path = self.active_sandboxes.pop(sandbox_id, None)
        if path and path.exists():
            shutil.rmtree(path, ignore_errors=True)
            return True
        return False

    def cleanup_all(self) -> None:
        for sandbox_id in list(self.active_sandboxes.keys()):
            self.cleanup_sandbox(sandbox_id)

    def status(self) -> Dict[str, Any]:
        return {
            "active_count": len(self.active_sandboxes),
            "sandbox_ids": list(self.active_sandboxes.keys()),
            "storage_path": str(self.sandbox_base),
        }