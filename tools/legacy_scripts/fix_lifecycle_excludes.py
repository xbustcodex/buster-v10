from pathlib import Path

ROOT = Path.cwd()

SCANNER = ROOT / "buster" / "lifecycle" / "scanner.py"
BACKUP = ROOT / "buster" / "lifecycle" / "backup.py"

scanner_code = r'''import fnmatch
import hashlib
import os
from pathlib import Path


class LifecycleScanner:
    def __init__(self, root: Path, exclude_patterns=None):
        self.root = Path(root)
        self.exclude_patterns = exclude_patterns or []

    def should_exclude(self, rel_path: str) -> bool:
        rel_path = str(rel_path).replace("\\", "/")
        name = Path(rel_path).name

        for pattern in self.exclude_patterns:
            pattern = str(pattern).replace("\\", "/").strip()

            if not pattern:
                continue

            if fnmatch.fnmatch(name, pattern):
                return True

            if fnmatch.fnmatch(rel_path, pattern):
                return True

            if rel_path == pattern:
                return True

            if rel_path.startswith(pattern.rstrip("/") + "/"):
                return True

        return False

    def hash_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def scan(self) -> dict:
        files = []
        hashes = {}
        total_size = 0

        for root, dirs, filenames in os.walk(self.root):
            root_path = Path(root)
            rel_root = root_path.relative_to(self.root).as_posix()

            dirs[:] = [
                d for d in dirs
                if not self.should_exclude(d if rel_root == "." else f"{rel_root}/{d}")
            ]

            for filename in filenames:
                file_path = root_path / filename
                rel_file = file_path.relative_to(self.root).as_posix()

                if self.should_exclude(rel_file):
                    continue

                try:
                    size = file_path.stat().st_size
                    file_hash = self.hash_file(file_path)
                except Exception:
                    continue

                files.append(rel_file)
                hashes[rel_file] = file_hash
                total_size += size

        return {
            "root": str(self.root),
            "files": files,
            "hashes": hashes,
            "size": total_size,
            "count": len(files)
        }
'''

backup_code = r'''import json
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
'''

SCANNER.parent.mkdir(parents=True, exist_ok=True)
BACKUP.parent.mkdir(parents=True, exist_ok=True)

SCANNER.write_text(scanner_code, encoding="utf-8")
BACKUP.write_text(backup_code, encoding="utf-8")

print("Fixed:")
print(" - buster/lifecycle/scanner.py")
print(" - buster/lifecycle/backup.py")
print()
print("Now run:")
print(" python run_lifecycle.py scan")
print(" python run_lifecycle.py backup")