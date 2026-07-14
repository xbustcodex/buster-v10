from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json


class SafeConfig:
    def __init__(self, path: str | Path = "data/v6_safe_config.json") -> None:
        self.path = Path(path)
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.data = {}
        return self.data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> Any:
        self.data[key] = value
        self.save()
        return value

    def status(self) -> Dict[str, Any]:
        return {"path": str(self.path), "keys": sorted(self.data.keys())}
