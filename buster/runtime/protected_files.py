from pathlib import Path

PROTECTED_PATHS = {
    "main.py",
    "buster/core",
    "buster/runtime",
}

PROTECTED_FILES = {
    "buster/runtime/self_improvement_runtime.py",
    "buster/runtime/core.py",
    "buster/runtime/__init__.py",
}


def is_protected(path: str) -> bool:
    p = Path(path).as_posix()

    if p in PROTECTED_FILES:
        return True

    return any(
        p.startswith(prefix)
        for prefix in PROTECTED_PATHS
    )