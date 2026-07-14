from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .registry import PluginRegistry


class PluginMarketplace:
    """Simple local marketplace index for future installable capabilities."""

    def __init__(self, index_path: str | Path = "data/plugin_marketplace.json") -> None:
        self.index_path = Path(index_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.items: List[Dict[str, Any]] = self._load()
        if not self.items:
            self._seed_defaults()

    def _load(self) -> List[Dict[str, Any]]:
        if not self.index_path.exists():
            return []
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else data.get("plugins", [])
        except Exception:
            return []

    def save(self) -> None:
        self.index_path.write_text(json.dumps({"plugins": self.items}, indent=2), encoding="utf-8")

    def _seed_defaults(self) -> None:
        self.items = [
            {
                "name": "android",
                "module": "buster.plugins.builtin.android_plugin",
                "description": "Android Studio, Gradle, APK, Logcat and emulator workflows.",
                "capabilities": ["android", "gradle", "apk", "logcat"],
            },
            {
                "name": "esp32",
                "module": "buster.plugins.builtin.esp32_plugin",
                "description": "ESP32, Arduino, firmware and serial workflows.",
                "capabilities": ["esp32", "arduino", "firmware", "serial"],
            },
            {
                "name": "github",
                "module": "buster.plugins.builtin.github_plugin",
                "description": "GitHub repository, issue and release workflows.",
                "capabilities": ["git", "github", "release", "repo"],
            },
        ]
        self.save()

    def search(self, query: str = "") -> List[Dict[str, Any]]:
        query_l = query.lower().strip()
        if not query_l:
            return self.items
        return [
            item for item in self.items
            if query_l in json.dumps(item).lower()
        ]

    def install(self, name: str, registry: Optional[PluginRegistry] = None) -> Dict[str, Any]:
        registry = registry or PluginRegistry()
        for item in self.items:
            if item.get("name") == name:
                return registry.register(
                    name=item["name"],
                    module=item["module"],
                    capabilities=item.get("capabilities", []),
                    metadata={"description": item.get("description", ""), "source": "marketplace"},
                )
        raise KeyError(f"Marketplace plugin not found: {name}")
