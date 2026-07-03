from pathlib import Path
import subprocess
import sys
import json

class WorkspaceSnapshot:

    def __init__(self):
        self.root = Path.cwd()

    def _run(self, command):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=True
            )
            return result.stdout.strip() or result.stderr.strip()
        except Exception as exc:
            return str(exc)

    def git_branch(self):
        return self._run("git branch --show-current")

    def git_status(self):
        status = self._run("git status --porcelain")
        return "Clean" if status == "" else "Modified"

    def python_info(self):
        return sys.version.split()[0]

    def approved_folders(self):
        settings = self.root / "data" / "approved_folders.json"

        if not settings.exists():
            return 0

        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
            return len(data.get("folders", []))
        except Exception:
            return 0

    def build_exists(self):
        return (self.root / "dist" / "Buster" / "Buster.exe").exists()

    def installer_exists(self):
        return any(self.root.rglob("*.exe"))

    def project_index_exists(self):
        return (self.root / "data" / "project_index.json").exists()

    def settings_exists(self):
        return (self.root / "data" / "settings.json").exists()

    def snapshot(self):

        lines = []

        lines.append(f"Project: {self.root.name}")
        lines.append(f"Folder: {self.root}")

        lines.append("")
        lines.append("Git")
        lines.append(f"  Branch : {self.git_branch()}")
        lines.append(f"  Status : {self.git_status()}")

        lines.append("")
        lines.append("Python")
        lines.append(f"  Version : {self.python_info()}")

        lines.append("")
        lines.append("Workspace")

        lines.append(f"  Approved folders : {self.approved_folders()}")

        lines.append(
            f"  Project index : {'Yes' if self.project_index_exists() else 'No'}"
        )

        lines.append(
            f"  Settings : {'Yes' if self.settings_exists() else 'No'}"
        )

        lines.append("")
        lines.append("Build")

        lines.append(
            f"  EXE : {'Yes' if self.build_exists() else 'No'}"
        )

        lines.append(
            f"  Installer : {'Yes' if self.installer_exists() else 'No'}"
        )

        return "\n".join(lines)
