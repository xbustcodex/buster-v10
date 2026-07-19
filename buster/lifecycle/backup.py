import fnmatch
import json
import shutil
from datetime import datetime
from pathlib import Path


class BackupManager:
    def __init__(self, root: Path, backup_dir: Path, max_backups: int = 5):
        self.root = Path(root).resolve()
        self.backup_dir = Path(backup_dir).resolve()
        self.max_backups = max_backups
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = self.backup_dir / f"backup_{stamp}"
        target.mkdir(parents=True, exist_ok=True)

        # Standard baseline exclusions
        ignored_names = {
            ".git", "__pycache__", "venv", ".venv", "dist", "build",
            ".lifecycle_backups", ".lifecycle_cache", ".lifecycle_logs",
            "buster_workspace", "backups", "logs"
        }
        ignored_extensions = {"*.pyc", "*.spec"}

        def strict_ignore(directory, contents):
            current_dir = Path(directory).resolve()
            ignored_items = []

            # CRITICAL: Prevent copying the backup directory into itself
            if current_dir == self.backup_dir or self.backup_dir in current_dir.parents:
                return contents

            for item in contents:
                # 1. Match explicit directory/file names
                if item in ignored_names:
                    ignored_items.append(item)
                    continue
                
                # 2. Match wildcards/extensions
                if any(fnmatch.fnmatch(item, ext) for ext in ignored_extensions):
                    ignored_items.append(item)
                    continue

            return ignored_items

        shutil.copytree(
            self.root,
            target / "project",
            dirs_exist_ok=False,  # Set to False to catch unintended path collisions early
            ignore=strict_ignore
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