from pathlib import Path
import json

ROOT = Path.cwd()

files = {
    "buster/lifecycle/__init__.py": '''"""
Buster Desktop AI OS - Lifecycle Manager
"""

from .manager import LifecycleManager
''',

    "buster/lifecycle/models.py": '''from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Any


class ComponentType(Enum):
    CORE = "core"
    UI = "ui"
    MEMORY = "memory"
    VOICE = "voice"
    VISION = "vision"
    AGENTS = "agents"
    PLUGINS = "plugins"
    THEMES = "themes"
    ASSETS = "assets"
    DATABASE = "database"
    NETWORK = "network"
    SECURITY = "security"


class UpdateStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class UpgradePlan:
    from_version: str
    to_version: str
    operations: List[Dict[str, Any]]
    files_to_update: int
    files_to_delete: int
    files_to_create: int
    disk_required: int
    rollback_available: bool
    components_affected: List[str]


@dataclass
class HealthReport:
    overall_score: float
    runtime_score: float
    imports_score: float
    config_score: float
    plugins_score: float
    database_score: float
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    timestamp: str
''',

    "buster/lifecycle/config.py": '''import json
from pathlib import Path


DEFAULT_CONFIG = {
    "version_file": "version.json",
    "backup_directory": ".lifecycle_backups",
    "cache_directory": ".lifecycle_cache",
    "log_directory": ".lifecycle_logs",
    "history_file": "data/lifecycle_history.json",
    "health_file": "data/lifecycle_health.json",
    "manifest_file": "data/upgrade_manifest.json",
    "max_backups": 5,
    "verify_after_upgrade": True,
    "auto_rollback_on_failure": True,
    "exclude_patterns": [".git", "__pycache__", "*.pyc", ".env", "venv", ".venv"],
    "components": {
        "core": {"critical": True},
        "ui": {"critical": False},
        "memory": {"critical": True},
        "agents": {"critical": True},
        "plugins": {"critical": False},
        "themes": {"critical": False},
        "assets": {"critical": False}
    }
}


def load_config(root: Path) -> dict:
    config_path = root / "config" / "lifecycle_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if not config_path.exists():
        config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=4), encoding="utf-8")
        return DEFAULT_CONFIG.copy()

    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        loaded = {}

    config = DEFAULT_CONFIG.copy()
    config.update(loaded)
    return config
''',

    "buster/lifecycle/scanner.py": '''import fnmatch
import hashlib
from pathlib import Path


class LifecycleScanner:
    def __init__(self, root: Path, exclude_patterns=None):
        self.root = Path(root)
        self.exclude_patterns = exclude_patterns or []

    def should_exclude(self, path: Path) -> bool:
        text = str(path).replace("\\\\", "/")
        name = path.name

        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(name, pattern) or pattern in text:
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

        for path in self.root.rglob("*"):
            if self.should_exclude(path):
                continue

            if path.is_file():
                rel = path.relative_to(self.root).as_posix()
                try:
                    size = path.stat().st_size
                    file_hash = self.hash_file(path)
                except Exception:
                    continue

                files.append(rel)
                hashes[rel] = file_hash
                total_size += size

        return {
            "root": str(self.root),
            "files": files,
            "hashes": hashes,
            "size": total_size,
            "count": len(files)
        }
''',

    "buster/lifecycle/backup.py": '''import json
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
            ".lifecycle_backups",
            ".lifecycle_cache",
            ".lifecycle_logs",
            "venv",
            ".venv"
        )

        shutil.copytree(self.root, target / "project", dirs_exist_ok=True, ignore=ignored)

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
''',

    "buster/lifecycle/rollback.py": '''import shutil
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
''',

    "buster/lifecycle/planner.py": '''from .models import UpgradePlan


class UpgradePlanner:
    def __init__(self, current_version: str):
        self.current_version = current_version

    def create_plan(self, manifest: dict) -> UpgradePlan:
        operations = manifest.get("operations", [])
        target_version = manifest.get("version", self.current_version)

        update_count = sum(1 for op in operations if op.get("type") == "update_file")
        create_count = sum(1 for op in operations if op.get("type") in ["add_file", "create_folder"])
        delete_count = sum(1 for op in operations if op.get("type") == "delete_file")

        disk_required = max(1, len(operations) * 2)

        return UpgradePlan(
            from_version=self.current_version,
            to_version=target_version,
            operations=operations,
            files_to_update=update_count,
            files_to_delete=delete_count,
            files_to_create=create_count,
            disk_required=disk_required,
            rollback_available=True,
            components_affected=manifest.get("components", [])
        )
''',

    "buster/lifecycle/verifier.py": '''import hashlib
import json
from pathlib import Path


class LifecycleVerifier:
    def __init__(self, root: Path):
        self.root = Path(root)

    def hash_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def verify_manifest(self, manifest: dict) -> dict:
        errors = []
        warnings = []

        for file_info in manifest.get("files", []):
            rel = file_info.get("path")
            expected_hash = file_info.get("hash")

            if not rel:
                continue

            path = self.root / rel

            if not path.exists():
                errors.append(f"Missing file: {rel}")
                continue

            if expected_hash:
                actual = self.hash_file(path)
                if actual != expected_hash:
                    errors.append(f"Hash mismatch: {rel}")

        return {
            "passed": not errors,
            "errors": errors,
            "warnings": warnings
        }

    def verify_config(self) -> dict:
        errors = []

        for rel in ["config/lifecycle_config.json", "version.json"]:
            path = self.root / rel
            if path.exists():
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except Exception as e:
                    errors.append(f"Invalid JSON: {rel} - {e}")

        return {
            "passed": not errors,
            "errors": errors
        }
''',

    "buster/lifecycle/health.py": '''import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .models import HealthReport


class HealthManager:
    def __init__(self, root: Path):
        self.root = Path(root)

    def check(self) -> dict:
        issues = []
        warnings = []
        recommendations = []

        runtime_score = 100
        imports_score = 100
        config_score = 100
        plugins_score = 100
        database_score = 100

        required = [
            "buster",
            "buster/lifecycle",
            "version.json",
            "config/lifecycle_config.json"
        ]

        for rel in required:
            if not (self.root / rel).exists():
                issues.append(f"Missing required path: {rel}")

        try:
            import requests
            import packaging
        except Exception as e:
            imports_score = 60
            warnings.append(f"Optional dependency issue: {e}")
            recommendations.append("Run: pip install requests packaging colorama pyyaml")

        if issues:
            runtime_score = 60

        scores = [runtime_score, imports_score, config_score, plugins_score, database_score]
        overall = sum(scores) / len(scores)

        report = HealthReport(
            overall_score=overall,
            runtime_score=runtime_score,
            imports_score=imports_score,
            config_score=config_score,
            plugins_score=plugins_score,
            database_score=database_score,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )

        return asdict(report)

    def save(self, report: dict):
        path = self.root / "data" / "lifecycle_health.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=4), encoding="utf-8")
''',

    "buster/lifecycle/manager.py": '''import json
import shutil
from datetime import datetime
from pathlib import Path

from .backup import BackupManager
from .config import load_config
from .health import HealthManager
from .planner import UpgradePlanner
from .rollback import RollbackManager
from .scanner import LifecycleScanner
from .verifier import LifecycleVerifier


class LifecycleManager:
    def __init__(self, root=None):
        self.root = Path(root or Path.cwd()).resolve()
        self.config = load_config(self.root)

        self.backup_dir = self.root / self.config["backup_directory"]
        self.cache_dir = self.root / self.config["cache_directory"]
        self.log_dir = self.root / self.config["log_directory"]

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.version = self.load_version()

        self.scanner = LifecycleScanner(self.root, self.config.get("exclude_patterns", []))
        self.backups = BackupManager(self.root, self.backup_dir, self.config.get("max_backups", 5))
        self.rollback_manager = RollbackManager(self.root)
        self.verifier = LifecycleVerifier(self.root)
        self.health = HealthManager(self.root)

    def load_version(self) -> str:
        version_file = self.root / self.config.get("version_file", "version.json")

        if not version_file.exists():
            version_file.write_text(json.dumps({
                "version": "9.1.0",
                "name": "Buster Desktop AI OS",
                "updated_at": datetime.now().isoformat(),
                "components": {}
            }, indent=4), encoding="utf-8")

        try:
            return json.loads(version_file.read_text(encoding="utf-8")).get("version", "0.0.0")
        except Exception:
            return "0.0.0"

    def save_version(self, version: str):
        version_file = self.root / self.config.get("version_file", "version.json")
        data = {
            "version": version,
            "name": "Buster Desktop AI OS",
            "updated_at": datetime.now().isoformat()
        }
        version_file.write_text(json.dumps(data, indent=4), encoding="utf-8")
        self.version = version

    def load_manifest(self) -> dict:
        manifest_path = self.root / self.config.get("manifest_file", "data/upgrade_manifest.json")

        if not manifest_path.exists():
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps({
                "version": self.version,
                "components": [],
                "operations": [],
                "files": [],
                "requires_restart": False
            }, indent=4), encoding="utf-8")

        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def status(self) -> dict:
        scan = self.scanner.scan()
        return {
            "version": self.version,
            "root": str(self.root),
            "files": scan["count"],
            "size": scan["size"],
            "backups": len([p for p in self.backup_dir.iterdir() if p.is_dir()])
        }

    def plan(self) -> dict:
        manifest = self.load_manifest()
        planner = UpgradePlanner(self.version)
        plan = planner.create_plan(manifest)
        return plan.__dict__

    def backup(self) -> str:
        return str(self.backups.create_backup())

    def verify(self) -> dict:
        manifest = self.load_manifest()
        manifest_result = self.verifier.verify_manifest(manifest)
        config_result = self.verifier.verify_config()

        return {
            "passed": manifest_result["passed"] and config_result["passed"],
            "manifest": manifest_result,
            "config": config_result
        }

    def apply_manifest(self, auto_confirm=False) -> bool:
        manifest = self.load_manifest()
        plan = self.plan()

        if not auto_confirm:
            print(json.dumps(plan, indent=4))
            answer = input("Apply this lifecycle manifest? [y/N]: ").strip().lower()
            if answer != "y":
                print("Cancelled.")
                return False

        backup_path = self.backup()
        print(f"Backup created: {backup_path}")

        try:
            for op in manifest.get("operations", []):
                op_type = op.get("type")
                destination = op.get("destination")
                source = op.get("source")

                if not destination:
                    continue

                dst = self.root / destination

                if op_type == "create_folder":
                    dst.mkdir(parents=True, exist_ok=True)

                elif op_type in ["add_file", "update_file"]:
                    if not source:
                        raise ValueError(f"Missing source for operation: {op}")

                    src = self.cache_dir / source

                    if not src.exists():
                        raise FileNotFoundError(f"Missing cached source file: {src}")

                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)

                elif op_type == "delete_file":
                    if dst.exists() and dst.is_file():
                        dst.unlink()

            verify_result = self.verify()

            if not verify_result["passed"]:
                raise RuntimeError(f"Verification failed: {verify_result}")

            if manifest.get("version"):
                self.save_version(manifest["version"])

            self.write_history("completed", manifest.get("version", self.version))
            return True

        except Exception as e:
            self.write_history("failed", manifest.get("version", self.version), str(e))

            if self.config.get("auto_rollback_on_failure", True):
                self.rollback_manager.rollback(Path(backup_path))

            print(f"Upgrade failed: {e}")
            return False

    def rollback(self) -> bool:
        latest = self.backups.latest_backup()

        if not latest:
            print("No backup available.")
            return False

        result = self.rollback_manager.rollback(latest)
        self.write_history("rolled_back", self.version, str(latest))
        return result

    def run_health(self) -> dict:
        report = self.health.check()
        self.health.save(report)
        return report

    def write_history(self, status: str, version: str, note: str = ""):
        history_path = self.root / self.config.get("history_file", "data/lifecycle_history.json")
        history_path.parent.mkdir(parents=True, exist_ok=True)

        if history_path.exists():
            try:
                history = json.loads(history_path.read_text(encoding="utf-8"))
            except Exception:
                history = []
        else:
            history = []

        history.append({
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "version": version,
            "note": note
        })

        history_path.write_text(json.dumps(history, indent=4), encoding="utf-8")
''',

    "buster/lifecycle/cli.py": '''import argparse
import json

from .manager import LifecycleManager


def main():
    parser = argparse.ArgumentParser(description="Buster Lifecycle Manager")
    parser.add_argument("command", nargs="?", default="status")
    parser.add_argument("--root", default=".")
    parser.add_argument("--yes", action="store_true")

    args = parser.parse_args()

    manager = LifecycleManager(args.root)

    if args.command == "status":
        print(json.dumps(manager.status(), indent=4))

    elif args.command == "scan":
        print(json.dumps(manager.scanner.scan(), indent=4))

    elif args.command == "plan":
        print(json.dumps(manager.plan(), indent=4))

    elif args.command == "backup":
        print(manager.backup())

    elif args.command == "verify":
        print(json.dumps(manager.verify(), indent=4))

    elif args.command == "upgrade":
        ok = manager.apply_manifest(auto_confirm=args.yes)
        print("Upgrade completed." if ok else "Upgrade failed.")

    elif args.command == "rollback":
        ok = manager.rollback()
        print("Rollback completed." if ok else "Rollback failed.")

    elif args.command == "health":
        print(json.dumps(manager.run_health(), indent=4))

    else:
        print("Commands: status, scan, plan, backup, verify, upgrade, rollback, health")


if __name__ == "__main__":
    main()
''',

    "run_lifecycle.py": '''from buster.lifecycle.cli import main

if __name__ == "__main__":
    main()
'''
}

data_files = {
    "data/lifecycle_history.json": [],
    "data/lifecycle_health.json": {},
    "data/upgrade_manifest.json": {
        "version": "9.1.0",
        "components": ["core", "ui", "agents"],
        "requires_restart": False,
        "operations": [],
        "files": []
    },
    "version.json": {
        "version": "9.1.0",
        "name": "Buster Desktop AI OS",
        "components": {
            "core": "9.1.0",
            "ui": "9.1.0",
            "agents": "9.1.0",
            "lifecycle": "1.0.0"
        }
    }
}

for rel, content in files.items():
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"created: {rel}")

for rel, content in data_files.items():
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(content, indent=4), encoding="utf-8")
        print(f"created: {rel}")
    else:
        print(f"exists:  {rel}")

print()
print("Lifecycle Manager installed.")
print()
print("Test it with:")
print("  python run_lifecycle.py status")
print("  python run_lifecycle.py scan")
print("  python run_lifecycle.py plan")
print("  python run_lifecycle.py backup")
print("  python run_lifecycle.py verify")
print("  python run_lifecycle.py health")