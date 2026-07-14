import json
from pathlib import Path
from typing import Any, Dict, List


def read_json(path: Path, default: Any):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def count_items(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ("items", "records", "events", "plugins", "experiences", "patterns", "strategies"):
            found = value.get(key)
            if isinstance(found, list):
                return len(found)
            if isinstance(found, dict):
                return len(found)
        return len(value)
    return 0
