class WorldModelWidgetModel:
    def __init__(self, snapshot=None):
        self.snapshot = snapshot or {}

    def as_lines(self):
        understanding = self.snapshot.get("understanding", {})
        context = understanding.get("context", {})
        lines = [
            "WORLD MODEL",
            f"Mode: {context.get('mode', 'unknown')}",
            f"Signals: {', '.join(context.get('signals', [])) or 'none'}",
            f"Recommendation: {understanding.get('recommendation', 'none')}",
        ]
        return lines
