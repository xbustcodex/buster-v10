import shutil
from pathlib import Path


class RollbackManager:
    def __init__(self, root: Path):
        self.root = Path(root)

    def rollback(self, backup_path: Path) -> bool:
        backup_project = Path(backup_path) / "project"

        if not backup_project.exists():
            return False

        for item in self.root.iterdir():
            if item.name in [".git", ".lifecycle_backups"]:
                continue

            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                try:
                    item.unlink()
                except Exception:
                    pass

        shutil.copytree(backup_project, self.root, dirs_exist_ok=True)
        return True
