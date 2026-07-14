from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List

def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def load_json(path: Path, default: Any) -> Any:
    ensure_parent(path)
    if not path.exists():
        save_json(path, default)
        return default
    try:
        text = path.read_text(encoding="utf-8").strip()
        return json.loads(text) if text else default
    except Exception:
        return default

def save_json(path: Path, data: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def append_json_list(path: Path, item: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = load_json(path, [])
    if not isinstance(data, list):
        data = []
    data.append(item)
    save_json(path, data)
    return data
