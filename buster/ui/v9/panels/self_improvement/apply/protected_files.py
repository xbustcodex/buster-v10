from __future__ import annotations

from pathlib import Path
from typing import Iterable


class ProtectedFileError(RuntimeError):
    """Raised when an unapproved patch targets Buster's protected core."""


# Paths are project-relative and use POSIX separators.
PROTECTED_FILES: frozenset[str] = frozenset(
    {
        "main.py",
        "launcher.py",
        "buster/runtime/self_improvement_runtime.py",
        "buster/runtime/core.py",
        "buster/runtime/__init__.py",
        "buster/core/runtime.py",
        "buster/plugins/loader.py",
    }
)

PROTECTED_DIRECTORIES: tuple[str, ...] = (
    "buster/core/",
    "buster/runtime/",
    "buster/plugins/",
)


def normalize_project_path(
    path: str | Path,
    project_root: str | Path,
) -> str:
    root = Path(project_root).expanduser().resolve()
    candidate = Path(path).expanduser()

    if not candidate.is_absolute():
        candidate = root / candidate

    resolved = candidate.resolve()

    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"Path is outside project root: {resolved}"
        ) from exc

    return relative.as_posix()


def is_protected(
    path: str | Path,
    project_root: str | Path,
) -> bool:
    relative = normalize_project_path(path, project_root)

    if relative in PROTECTED_FILES:
        return True

    return any(
        relative.startswith(directory)
        for directory in PROTECTED_DIRECTORIES
    )


def find_protected_paths(
    paths: Iterable[str | Path],
    project_root: str | Path,
) -> list[Path]:
    root = Path(project_root).expanduser().resolve()
    protected: list[Path] = []

    for value in paths:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate

        resolved = candidate.resolve()
        if is_protected(resolved, root):
            protected.append(resolved)

    return protected


__all__ = [
    "PROTECTED_DIRECTORIES",
    "PROTECTED_FILES",
    "ProtectedFileError",
    "find_protected_paths",
    "is_protected",
    "normalize_project_path",
]
