from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any, Dict


class RuntimeStateStore:
    """
    Thread-safe shared state for Buster's runtime and UI.

    Panels read from this store instead of independently querying every
    runtime subsystem.
    """

    def __init__(self):
        self._lock = RLock()

        self._state: Dict[str, Any] = {
            "runtime": {
                "started": False,
                "status": "ready",
                "root": None,
            },
            "jobs": {
                "count": 0,
                "counts": {},
                "jobs": [],
            },
            "agents": {
                "count": 0,
                "agents": [],
                "active": {},
            },
            "memory": {},
            "blackboard": {},
            "registry": {},
            "services": {},
            "voice": {
                "status": "ready",
            },
            "vision": {
                "status": "ready",
            },
            "face": {
                "state": "idle",
                "message": "Buster is ready.",
            },
            "notification": None,
            "last_event": None,
        }

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return deepcopy(self._state.get(key, default))

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._state[key] = deepcopy(value)

    def update(self, key: str, values: Dict[str, Any]) -> None:
        with self._lock:
            current = self._state.get(key)

            if not isinstance(current, dict):
                current = {}

            current.update(deepcopy(values))
            self._state[key] = current

    def remove(self, key: str) -> None:
        with self._lock:
            self._state.pop(key, None)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self._state)

    def clear(self) -> None:
        with self._lock:
            self._state.clear()

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "sections": sorted(self._state.keys()),
                "section_count": len(self._state),
            }