from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
DATA_DIR = Path('data')
def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')
def load_json(path: Path, default: Any) -> Any:
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return default
def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
def append_json(path: Path, item: Any, limit: int = 500) -> list:
    items = load_json(path, [])
    if not isinstance(items, list): items = []
    items.append(item)
    items = items[-limit:]
    save_json(path, items)
    return items
