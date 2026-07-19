from __future__ import annotations

import ast
import re
import shutil
from datetime import datetime
from pathlib import Path


PROJECT_MARKER = Path("buster/ui/v9/panels/self_improvement")
SESSION_CLASS = "RepairSessionStore"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def find_project_root(start: Path) -> Path:
    current = start.expanduser().resolve()

    for candidate in (current, *current.parents):
        if (candidate / PROJECT_MARKER).exists():
            return candidate

    raise FileNotFoundError(
        "Could not locate the Buster project root. "
        "Run this script from inside C:\\Users\\xkali\\new_ai\\buster-v10"
    )


def backup_tree(source_root: Path, project_root: Path) -> Path:
    backup_root = (
        project_root
        / "data"
        / "migration_backups"
        / f"self_improvement_reorg_{timestamp()}"
    )
    backup_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_root, backup_root)
    return backup_root


def move_file(source: Path, destination: Path) -> None:
    if not source.exists():
        print(f"[SKIP] Missing: {source}")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        raise FileExistsError(
            f"Destination already exists: {destination}"
        )

    shutil.move(str(source), str(destination))
    print(f"[MOVE] {source.name} -> {destination}")


def get_class_line_range(source: str, class_name: str) -> tuple[int, int]:
    tree = ast.parse(source)

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            if node.end_lineno is None:
                raise RuntimeError(
                    f"Unable to determine end of class {class_name}."
                )
            return node.lineno, node.end_lineno

    raise RuntimeError(f"Class {class_name} not found.")


def split_repair_session(
    repair_session_file: Path,
    store_file: Path,
) -> None:
    source = repair_session_file.read_text(encoding="utf-8")
    lines = source.splitlines()

    start_line, end_line = get_class_line_range(
        source,
        SESSION_CLASS,
    )

    class_lines = lines[start_line - 1:end_line]
    session_lines = lines[:start_line - 1] + lines[end_line:]
    session_text = "\n".join(session_lines).rstrip() + "\n"

    session_text = re.sub(
        r"\n__all__\s*=\s*\[[\s\S]*?\]\s*$",
        "",
        session_text,
        flags=re.MULTILINE,
    ).rstrip()

    session_text += '''

__all__ = [
    "RepairSession",
    "RepairSessionEvent",
    "RepairSessionStage",
    "RepairSessionStatus",
]
'''

    store_text = '''from __future__ import annotations

from pathlib import Path

from .repair_session import RepairSession


''' + "\n".join(class_lines).rstrip()

    store_text += '''


__all__ = [
    "RepairSessionStore",
]
'''

    repair_session_file.write_text(
        session_text.lstrip(),
        encoding="utf-8",
    )
    store_file.write_text(
        store_text.lstrip(),
        encoding="utf-8",
    )

    print("[SPLIT] RepairSessionStore -> repair_session_store.py")


def create_session_manager(path: Path) -> None:
    content = '''from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from .repair_session import RepairSession
from .repair_session_store import RepairSessionStore


class SessionManager:
    """Creates, saves, resumes, lists and removes repair sessions."""

    def __init__(
        self,
        project_root: str | Path,
        sessions_root: str | Path | None = None,
    ) -> None:
        self.project_root = Path(
            project_root
        ).expanduser().resolve()

        self.store = RepairSessionStore(
            project_root=self.project_root,
            sessions_root=sessions_root,
        )

    def create(
        self,
        finding: Any,
        *,
        metadata: Optional[Mapping[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> RepairSession:
        session = RepairSession.create(
            project_root=self.project_root,
            finding=finding,
            metadata=metadata,
            session_id=session_id,
        )
        self.store.save(session)
        return session

    def save(self, session: RepairSession) -> Path:
        return self.store.save(session)

    def resume(self, session_id: str) -> RepairSession:
        return self.store.load(session_id)

    def latest(
        self,
        *,
        include_completed: bool = True,
    ) -> RepairSession | None:
        return self.store.latest(
            include_completed=include_completed
        )

    def active(self) -> list[RepairSession]:
        return self.store.active_sessions()

    def list_all(self) -> list[RepairSession]:
        return self.store.list_sessions(
            include_completed=True
        )

    def delete(self, session_id: str) -> bool:
        return self.store.delete(session_id)


__all__ = [
    "SessionManager",
]
'''
    path.write_text(content, encoding="utf-8")
    print("[CREATE] session_manager.py")


def update_imports(project_root: Path) -> int:
    replacements = {
        "buster.ui.v9.panels.self_improvement.session.repair_session":
            "buster.ui.v9.panels.self_improvement.session.repair_session",
        "from .session.repair_session import":
            "from .session.repair_session import",
        "from ..session.repair_session import":
            "from ..session.repair_session import",
        "from .repair_session_store import RepairSessionStore":
            "from .repair_session_store import RepairSessionStore",
    }

    changed = 0

    for path in project_root.rglob("*.py"):
        if any(
            part in {
                ".git",
                "__pycache__",
                ".venv",
                "venv",
                "build",
                "dist",
            }
            for part in path.parts
        ):
            continue

        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        updated = original
        for old, new in replacements.items():
            updated = updated.replace(old, new)

        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
            print(f"[IMPORT] Updated {path.relative_to(project_root)}")

    return changed


def compile_package(path: Path) -> None:
    failures = []

    for file_path in path.rglob("*.py"):
        try:
            source = file_path.read_text(encoding="utf-8")
            compile(source, str(file_path), "exec")
        except Exception as exc:
            failures.append((file_path, exc))

    if failures:
        messages = "\n".join(
            f"  - {file_path}: {exc}"
            for file_path, exc in failures
        )
        raise RuntimeError(
            "Syntax validation failed:\n" + messages
        )


def write_package_files(
    verification: Path,
    session: Path,
    apply_package: Path,
) -> None:
    session_init = '''"""Repair session orchestration."""

from .repair_session import (
    RepairSession,
    RepairSessionEvent,
    RepairSessionStage,
    RepairSessionStatus,
)
from .repair_session_store import RepairSessionStore
from .session_manager import SessionManager

__all__ = [
    "RepairSession",
    "RepairSessionEvent",
    "RepairSessionStage",
    "RepairSessionStatus",
    "RepairSessionStore",
    "SessionManager",
]
'''
    (session / "__init__.py").write_text(
        session_init,
        encoding="utf-8",
    )

    verification_init = '''"""Post-apply verification pipeline."""

from .behavioral_checker import BehavioralChecker
from .formatter_checker import FormatterChecker
from .import_checker import ImportChecker
from .lint_checker import LintChecker
from .syntax_checker import SyntaxChecker
from .unit_test_runner import UnitTestRunner
from .verification_engine import VerificationEngine
from .verification_report import VerificationReport
from .verification_worker import VerificationWorker

__all__ = [
    "BehavioralChecker",
    "FormatterChecker",
    "ImportChecker",
    "LintChecker",
    "SyntaxChecker",
    "UnitTestRunner",
    "VerificationEngine",
    "VerificationReport",
    "VerificationWorker",
]
'''
    (verification / "__init__.py").write_text(
        verification_init,
        encoding="utf-8",
    )

    exports = []
    for module_name, class_name in (
        ("apply_changes_worker", "ApplyChangesWorker"),
        ("backup_manager", "BackupManager"),
        ("rollback_manager", "RollbackManager"),
        ("change_manifest", "ChangeManifest"),
        ("patch_applier", "PatchApplier"),
    ):
        if (apply_package / f"{module_name}.py").exists():
            exports.append((module_name, class_name))

    lines = ['"""Safe change application and rollback pipeline."""', ""]

    for module_name, class_name in exports:
        lines.append(
            f"from .{module_name} import {class_name}"
        )

    lines.extend(["", "__all__ = ["])

    for _, class_name in exports:
        lines.append(f'    "{class_name}",')

    lines.append("]")

    (apply_package / "__init__.py").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    try:
        project_root = find_project_root(Path.cwd())
        self_improvement = project_root / PROJECT_MARKER
        verification = self_improvement / "verification"
        session = self_improvement / "session"
        apply_package = self_improvement / "apply"

        print("=" * 72)
        print("Buster Self Improvement Package Reorganisation")
        print("=" * 72)
        print(f"Project root: {project_root}")

        backup = backup_tree(
            self_improvement,
            project_root,
        )
        print(f"[BACKUP] {backup}")

        session.mkdir(parents=True, exist_ok=True)
        apply_package.mkdir(parents=True, exist_ok=True)
        verification.mkdir(parents=True, exist_ok=True)

        move_file(
            verification / "repair_session.py",
            session / "repair_session.py",
        )

        split_repair_session(
            session / "repair_session.py",
            session / "repair_session_store.py",
        )

        create_session_manager(
            session / "session_manager.py"
        )

        apply_files = [
            "apply_changes_worker.py",
            "backup_manager.py",
            "rollback_manager.py",
            "change_manifest.py",
            "patch_applier.py",
        ]

        for filename in apply_files:
            candidates = [
                verification / filename,
                self_improvement / filename,
            ]

            source = next(
                (
                    candidate
                    for candidate in candidates
                    if candidate.exists()
                ),
                None,
            )

            if source is None:
                print(f"[SKIP] Could not locate {filename}")
                continue

            move_file(
                source,
                apply_package / filename,
            )

        write_package_files(
            verification,
            session,
            apply_package,
        )

        imports_changed = update_imports(project_root)
        compile_package(self_improvement)

        print()
        print("=" * 72)
        print("REORGANISATION COMPLETE")
        print("=" * 72)
        print(f"Backup: {backup}")
        print(f"Imports updated: {imports_changed}")
        print("Syntax validation: PASSED")
        print()
        print("New packages:")
        print("  self_improvement/session/")
        print("  self_improvement/apply/")
        print("  self_improvement/verification/")
        return 0

    except Exception as exc:
        print()
        print(f"[FAILED] {exc}")
        print(
            "The self_improvement folder is backed up before "
            "any migration changes are made."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
