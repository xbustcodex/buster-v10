from __future__ import annotations

from typing import Any, Dict


class PluginInspector:
    def __init__(self, core):
        self.core = core

    def status(self) -> Dict[str, Any]:
        host = self.core.service("plugin_host")

        if host is None:
            return {
                "available": False,
                "plugins": {},
                "count": 0,
            }

        if hasattr(host, "status"):
            data = host.status()
            data["available"] = True
            return data

        return {
            "available": True,
            "plugins": {},
            "count": 0,
        }
