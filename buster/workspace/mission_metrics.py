import json
from pathlib import Path
from typing import Any, Dict, List


class MissionMetrics:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)

    def _load_json(self, name: str, default: Any) -> Any:
        path = self.data_dir / name
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def _count_items(self, value: Any) -> int:
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            for key in ("items", "records", "entries", "history", "events", "patterns", "strategies", "plugins", "skills"):
                if isinstance(value.get(key), list):
                    return len(value[key])
                if isinstance(value.get(key), dict):
                    return len(value[key])
            return len(value)
        return 0

    def collect(self) -> Dict[str, Any]:
        learning = self._load_json("learning_memory.json", [])
        experience = self._load_json("experience_memory.json", [])
        skills = self._load_json("skill_profiles.json", {})
        plugins = self._load_json("plugin_registry.json", {})
        autonomy = self._load_json("autonomy_state.json", {})
        intelligence = self._load_json("intelligence_state.json", {})
        events = self._load_json("event_history.json", [])

        return {
            "learning_entries": self._count_items(learning),
            "experience_entries": self._count_items(experience),
            "skills_tracked": self._count_items(skills),
            "plugins_loaded": self._count_items(plugins),
            "running_jobs": self._count_items(autonomy.get("running_jobs", [])) if isinstance(autonomy, dict) else 0,
            "active_agents": self._count_items(autonomy.get("active_agents", [])) if isinstance(autonomy, dict) else 0,
            "confidence": intelligence.get("confidence", 0.0) if isinstance(intelligence, dict) else 0.0,
            "risk": intelligence.get("risk", "unknown") if isinstance(intelligence, dict) else "unknown",
            "event_count": self._count_items(events),
        }
