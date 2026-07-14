from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from datetime import datetime, timezone

DATA_DIR = Path("data")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: str | Path, default: Any) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def append_record(path: str | Path, record: Dict[str, Any], limit: int = 500) -> Dict[str, Any]:
    records = load_json(path, [])
    if not isinstance(records, list):
        records = []
    records.append(record)
    if len(records) > limit:
        records = records[-limit:]
    save_json(path, records)
    return record
