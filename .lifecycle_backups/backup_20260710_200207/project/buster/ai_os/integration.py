from typing import Any, Dict


class AIOSIntegration:
    """Connects v3 systems without forcing direct imports everywhere."""

    def __init__(self, context):
        self.context = context

    def summarize(self) -> Dict[str, Any]:
        from .storage import read_json, count_items
        learning = read_json(self.context.data_path("learning_memory.json"), {})
        experience = read_json(self.context.data_path("experience_memory.json"), {})
        events = read_json(self.context.data_path("event_history.json"), {})
        plugins = read_json(self.context.data_path("plugin_registry.json"), {})
        mission = read_json(self.context.data_path("mission_control_dashboard.json"), {})
        return {
            "learning_items": count_items(learning),
            "experience_items": count_items(experience),
            "events_recorded": count_items(events),
            "plugins_loaded": count_items(plugins),
            "mission": mission,
        }
