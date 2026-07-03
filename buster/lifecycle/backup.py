import json
import shutil
from datetime import datetime
from pathlib import Path


class BackupManager:
    def __init__(self, root: Path, backup_dir: Path, max_backups: int = 5):
        self.root = Path(root)
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = self.backup_dir / f"backup_{stamp}"
        target.mkdir(parents=True, exist_ok=True)

        ignored = shutil.ignore_patterns(
            ".git",
            "__pycache__",
            "*.pyc",
            ".env",
            "venv",
            ".venv",
            "dist",
            "dist/*",
            "build",
            "build/*",
            "*.spec",
            ".lifecycle_backups",
            ".lifecycle_cache",
            ".lifecycle_logs",
            "buster_workspace",
            "backups",
            "logs"
        )

        shutil.copytree(
            self.root,
            target / "project",
            dirs_exist_ok=True,
            ignore=ignored
        )

        metadata = {
            "created_at": datetime.now().isoformat(),
            "source": str(self.root),
            "backup": str(target)
        }

        (target / "backup_metadata.json").write_text(
            json.dumps(metadata, indent=4),
            encoding="utf-8"
        )

        self.cleanup_old_backups()
        return target

    def cleanup_old_backups(self):
        backups = sorted(
            [p for p in self.backup_dir.iterdir() if p.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for old in backups[self.max_backups:]:
            shutil.rmtree(old, ignore_errors=True)

    def latest_backup(self):
        backups = sorted(
            [p for p in self.backup_dir.iterdir() if p.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        return backups[0] if backups else None
