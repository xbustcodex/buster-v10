from __future__ import annotations

import importlib
from typing import Any, Dict, List

from .registry import PluginRegistry


class PluginLoader:
    """Loads enabled plugins without bloating Buster core."""

    def __init__(self, registry: PluginRegistry | None = None) -> None:
        self.registry = registry or PluginRegistry()
        self.loaded: Dict[str, Any] = {}

    def load_enabled(self) -> Dict[str, Any]:
        for plugin in self.registry.list_plugins(enabled_only=True):
            self.load_plugin(plugin["name"])
        return self.loaded

    def load_plugin(self, name: str) -> Any:
        plugin = self.registry.plugins.get(name)
        if not plugin:
            raise KeyError(f"Plugin not registered: {name}")
        module_name = plugin["module"]
        module = importlib.import_module(module_name)

        if hasattr(module, "create_plugin"):
            instance = module.create_plugin()
        elif hasattr(module, "Plugin"):
            instance = module.Plugin()
        else:
            instance = module

        self.loaded[name] = instance
        return instance

    def commands(self) -> Dict[str, Any]:
        commands: Dict[str, Any] = {}
        for name, plugin in self.loaded.items():
            if hasattr(plugin, "commands"):
                value = plugin.commands
                commands[name] = value() if callable(value) else value
        return commands
