from __future__ import annotations

import shutil
from pathlib import Path

FILES = {
    "apply_changes_worker.py": "apply.apply_changes_worker",
    "backup_manager.py": "apply.backup_manager",
    "rollback_manager.py": "apply.rollback_manager",
    "change_manifest.py": "apply.change_manifest",
    "patch_applier.py": "apply.patch_applier",
    "repair_session.py": "session.repair_session",
    "repair_session_store.py": "session.repair_session_store",
    "session_manager.py": "session.session_manager",
}


def find_project_root(start: Path) -> Path:
    start = start.resolve()
    for candidate in (start, *start.parents):
        marker = candidate / 'buster' / 'ui' / 'v9' / 'panels' / 'self_improvement'
        if marker.is_dir():
            return candidate
    raise RuntimeError('Run this script from the buster-v10 project folder.')


def main() -> int:
    root = find_project_root(Path.cwd())
    target = root / 'buster' / 'ui' / 'v9' / 'panels' / 'self_improvement'
    backup = root / 'data' / 'compatibility_backup'
    backup.mkdir(parents=True, exist_ok=True)

    for filename, module_target in FILES.items():
        path = target / filename
        if path.exists():
            shutil.copy2(path, backup / filename)

        content = (
            "from __future__ import annotations\n\n"
            '"""Compatibility forwarding module.\n\n'
            f"Implementation moved to:\n\n    buster.ui.v9.panels.self_improvement.{module_target}\n"
            '"""\n\n'
            f"from .{module_target} import *  # noqa: F401,F403\n"
        )
        path.write_text(content, encoding='utf-8')
        compile(content, str(path), 'exec')
        print(f'[OK] {path.relative_to(root)}')

    print()
    print('Compatibility layer installed.')
    print(f'Previous files backed up to: {backup}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
