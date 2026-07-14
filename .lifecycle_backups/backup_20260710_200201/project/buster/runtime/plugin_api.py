from __future__ import annotations

from typing import Protocol, Any


class BusterPlugin(Protocol):
    name: str
    version: str

    def register(self, runtime) -> Any:
        ...


class PluginHost:
    def __init__(self, runtime):
        self.runtime = runtime
        self.plugins = {}

    def register_plugin(self, plugin):
        name = getattr(plugin, "name", plugin.__class__.__name__)
        result = plugin.register(self.runtime)
        self.plugins[name] = {
            "name": name,
            "version": getattr(plugin, "version", "0.0.0"),
            "plugin": plugin,
            "result": result,
        }

        self.runtime.events.publish(
            "plugin.registered",
            {
                "name": name,
                "version": self.plugins[name]["version"],
            },
            source="plugin_host",
        )

        return result

    def status(self):
        return {
            "count": len(self.plugins),
            "plugins": {
                name: {
                    "version": data["version"],
                    "result": data["result"],
                }
                for name, data in self.plugins.items()
            },
        }
