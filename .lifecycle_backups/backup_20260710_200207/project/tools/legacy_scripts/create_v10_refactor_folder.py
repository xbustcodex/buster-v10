from pathlib import Path
import shutil
import json
from datetime import datetime

SOURCE = Path.cwd()
TARGET = SOURCE.parent / "buster-v10-refactor"

COPY_DIRS = [
    ".github",
    "buster",
    "config",
    "data",
    "scripts",
    "tests",
    "installer",
    "assets",
]

COPY_FILES = [
    ".gitignore",
    "README.md",
    "requirements.txt",
    "pytest.ini",
    "main.py",
    "run_lifecycle.py",
    "run_v9_ui_preview.py",
    "version.json",
    "Buster.spec",
]

EXCLUDE_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".lifecycle_backups",
    ".lifecycle_cache",
    ".lifecycle_logs",
    "dist",
    "build",
    "venv",
    ".venv",
    "backups",
    "logs",
    "screenshots",
    "buster_workspace",
}

EXCLUDE_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
}

EXCLUDE_FILE_NAMES = {
    "tree.txt",
    "tree_v5_6.txt",
    "yolov8n.pt",
}

MOVE_ROOT_CLUTTER_TO_TOOLS = True

ROOT_TOOL_PREFIXES = (
    "apply_",
    "patch_",
    "setup_",
    "fix_",
    "wire_",
    "upgrade_",
    "create_",
    "debug_",
    "switch_",
)

DOC_PREFIXES = (
    "BUSTER_",
    "README_v",
    "README_DOCTOR",
)


def should_skip(path: Path) -> bool:
    parts = set(path.parts)

    if parts & EXCLUDE_DIR_NAMES:
        return True

    if path.name in EXCLUDE_FILE_NAMES:
        return True

    if path.suffix.lower() in EXCLUDE_FILE_SUFFIXES:
        return True

    if path.name.endswith(".bak_v31") or ".bak_" in path.name:
        return True

    return False


def copy_dir(src: Path, dst: Path):
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        target = dst / rel

        if should_skip(item):
            continue

        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def copy_file(src: Path, dst: Path):
    if src.exists() and src.is_file() and not should_skip(src):
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def copy_root_tools():
    tools_dir = TARGET / "tools" / "legacy_scripts"
    docs_dir = TARGET / "docs" / "legacy"

    for item in SOURCE.iterdir():
        if not item.is_file():
            continue

        name = item.name

        if name == Path(__file__).name:
            continue

        if name.startswith(ROOT_TOOL_PREFIXES) and item.suffix.lower() in {".py", ".ps1", ".bat"}:
            tools_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, tools_dir / name)

        elif name.startswith(DOC_PREFIXES) and item.suffix.lower() in {".md", ".txt"}:
            docs_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, docs_dir / name)


def write_v10_notes():
    notes = {
        "created_at": datetime.now().isoformat(),
        "source_project": str(SOURCE),
        "target_project": str(TARGET),
        "purpose": "Clean Buster Desktop AI OS v10 refactor workspace",
        "copied_dirs": COPY_DIRS,
        "copied_files": COPY_FILES,
        "excluded": sorted(EXCLUDE_DIR_NAMES),
        "next_steps": [
            "Run python run_lifecycle.py status",
            "Run python run_lifecycle.py health",
            "Run pytest",
            "Consolidate service manager",
            "Consolidate event bus",
            "Consolidate agent framework",
            "Wire Mission Control to services only"
        ]
    }

    (TARGET / "V10_REFACTOR_NOTES.json").write_text
        json.dumps(notes, indent=4),
        encoding="utf-8"
    )

    (TARGET / "README_V10_REFACTOR.md").write_text(
        ""# Buster Desktop AI OS v10 Refactor

This folder was created as a clean refactor workspace.

## Goal

Turn Buster into a service-based AI desktop platform.

## Main architecture targets

- One runtime
- One service manager
- One event bus
- One agent framework
- Mission Control as dashboard only
- Lifecycle Manager as core service
- Cleaner repository layout

## First tests

```bat
python run_lifecycle.py status
python run_lifecycle.py health
pytest