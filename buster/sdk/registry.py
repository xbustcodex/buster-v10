from __future__ import annotations

from typing import Any, Dict, Iterable


class ServiceRegistry:
    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}

    def register(self, name: str, service: Any, replace: bool = True) -> Any:
        if not replace and name in self._services:
            raise KeyError(f"Service already registered: {name}")
        self._services[name] = service
        return service

    def get(self, name: str, default: Any = None) -> Any:
        return self._services.get(name, default)

    def require(self, name: str) -> Any:
        if name not in self._services:
            raise KeyError(f"Missing required service: {name}")
        return self._services[name]

    def has(self, name: str) -> bool:
        return name in self._services

    def names(self) -> list[str]:
        return sorted(self._services.keys())

    def items(self) -> Iterable[tuple[str, Any]]:
        return self._services.items()

    def status(self) -> Dict[str, Any]:
        return {"services": self.names(), "count": len(self._services)}
