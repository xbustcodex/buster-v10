import json
from pathlib import Path


DEFAULT_EXCLUDES = [
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
    "logs",
    "installer",
    "release",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode"
]


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
    "exclude_patterns": DEFAULT_EXCLUDES,
    "components": {
        "core": {"critical": True},
        "ui": {"critical": False},
        "memory": {"critical": True},
        "agents": {"critical": True},
        "plugins": {"critical": False},
        "themes": {"critical": False},
        "assets": {"critical": False},
    },
}


def load_config(root: Path) -> dict:
    config_path = root / "config" / "lifecycle_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if not config_path.exists():
        config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=4), encoding="utf-8")
        return DEFAULT_CONFIG.copy()

    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"WARNING: Invalid lifecycle_config.json, using defaults: {e}")
        loaded = {}

    config = DEFAULT_CONFIG.copy()
    config.update(loaded)

    merged_excludes = list(dict.fromkeys(
        DEFAULT_EXCLUDES + loaded.get("exclude_patterns", [])
    ))
    config["exclude_patterns"] = merged_excludes

    return config