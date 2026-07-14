import json
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
