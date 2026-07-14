class PerceptionOSWidgetModel:
    def build(self, snapshot):
        return {
            "title": "Perception OS",
            "mode": snapshot.get("mode", "unknown"),
            "focus": snapshot.get("focus", "idle"),
            "importance": snapshot.get("importance", 0.0),
            "reason": snapshot.get("reason", ""),
        }
