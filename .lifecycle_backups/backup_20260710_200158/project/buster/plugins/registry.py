from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class PluginRegistry:
    """Persistent registry for installed Buster capabilities."""

    def __init__(self, path: str | Path = "data/plugin_registry.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.plugins: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "plugins" in data:
                return data["plugins"]
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save(self) -> None:
        self.path.write_text(json.dumps({"plugins": self.plugins}, indent=2), encoding="utf-8")

    def register(
        self,
        name: str,
        module: str,
        capabilities: Optional[List[str]] = None,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.plugins[name] = {
            "name": name,
            "module": module,
            "capabilities": capabilities or [],
            "enabled": enabled,
            "metadata": metadata or {},
        }
        self.save()
        return self.plugins[name]

    def unregister(self, name: str) -> bool:
        existed = name in self.plugins
        self.plugins.pop(name, None)
        self.save()
        return existed

    def enable(self, name: str, enabled: bool = True) -> None:
        if name in self.plugins:
            self.plugins[name]["enabled"] = enabled
            self.save()

    def list_plugins(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        items = list(self.plugins.values())
        if enabled_only:
            items = [item for item in items if item.get("enabled", True)]
        return items

    def find_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        capability_l = capability.lower()
        return [
            plugin for plugin in self.list_plugins(enabled_only=True)
            if any(capability_l in cap.lower() for cap in plugin.get("capabilities", []))
        ]
