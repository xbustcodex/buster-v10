from __future__ import annotations

from typing import Any, Dict, List

from .storage import load_json, save_json, now_iso

WORKING_MEMORY = "data/working_memory.json"


class WorkingMemory:
    """Small active context window: what Buster is thinking about now."""

    def __init__(self, path: str = WORKING_MEMORY, capacity: int = 12):
        self.path = path
        self.capacity = capacity

    def get_state(self) -> Dict[str, Any]:
        return load_json(self.path, {"items": [], "current_mission": None, "updated": now_iso()})

    def remember(self, item_type: str, title: str, data: Dict[str, Any] | None = None, priority: float = 0.5) -> Dict[str, Any]:
        state = self.get_state()
        item = {
            "type": item_type,
            "title": title,
            "data": data or {},
            "priority": round(float(priority), 3),
            "timestamp": now_iso(),
        }
        items = state.get("items", [])
        items.append(item)
        items = sorted(items, key=lambda x: (x.get("priority", 0), x.get("timestamp", "")), reverse=True)[: self.capacity]
        state["items"] = items
        state["updated"] = now_iso()
        save_json(self.path, state)
        return item

    def set_current_mission(self, mission: Dict[str, Any]) -> None:
        state = self.get_state()
        state["current_mission"] = mission
        state["updated"] = now_iso()
        save_json(self.path, state)

    def clear(self) -> None:
        save_json(self.path, {"items": [], "current_mission": None, "updated": now_iso()})

    def summary(self) -> Dict[str, Any]:
        state = self.get_state()
        return {
            "active_items": len(state.get("items", [])),
            "current_mission": state.get("current_mission"),
            "top_items": state.get("items", [])[:5],
            "updated": state.get("updated"),
        }
