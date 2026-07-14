import json
import time
from pathlib import Path
from typing import Any, Optional

class WebCache:
    def __init__(self, cache_file: str = "data/web_cache.json", ttl_seconds: int = 3600):
        self.cache_file = Path(cache_file)
        self.ttl_seconds = ttl_seconds
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if not self.cache_file.exists():
            return {}
        try:
            return json.loads(self.cache_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self) -> None:
        self.cache_file.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get(self, key: str) -> Optional[Any]:
        item = self._data.get(key)
        if not item:
            return None
        if time.time() - item.get("time", 0) > self.ttl_seconds:
            return None
        return item.get("value")

    def set(self, key: str, value: Any) -> None:
        self._data[key] = {"time": time.time(), "value": value}
        self._save()
