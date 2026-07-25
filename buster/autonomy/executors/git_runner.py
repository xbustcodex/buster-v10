from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


class GitOperationRunner:
    """Executes version control mission steps safely within the repository boundary."""

    def _run_git_cmd(self, repo_path: str | Path, args: List[str]) -> subprocess.CompletedProcess[str]:
        """Runs a git command in the target repository directory."""
        return subprocess.run(
            ["git"] + args,
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=False,
        )

    def get_status(self, repo_path: str | Path) -> Dict[str, Any]:
        """Gets short git status output."""
        res = self._run_git_cmd(repo_path, ["status", "--porcelain"])
        if res.returncode != 0:
            return {"status": "error", "message": res.stderr.strip()}

        changes = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        return {
            "status": "success",
            "has_changes": len(changes) > 0,
            "modified_files": changes,
        }

    def create_commit(
        self,
        repo_path: str | Path,
        message: str,
        files_to_stage: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Stages specified files (or all changes) and creates a git commit."""
        stage_args = ["add"] + (files_to_stage if files_to_stage else ["."])
        stage_res = self._run_git_cmd(repo_path, stage_args)

        if stage_res.returncode != 0:
            return {"status": "failed", "error": f"Git add failed: {stage_res.stderr.strip()}"}

        commit_res = self._run_git_cmd(repo_path, ["commit", "-m", message])
        if commit_res.returncode != 0:
            return {"status": "failed", "error": f"Git commit failed: {commit_res.stderr.strip()}"}

        return {
            "status": "success",
            "message": message,
            "output": commit_res.stdout.strip(),
        }