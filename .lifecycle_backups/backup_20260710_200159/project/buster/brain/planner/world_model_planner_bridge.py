from buster.world_model import WorldModelEngine

class WorldModelPlannerBridge:
    def __init__(self, data_dir="data"):
        self.world = WorldModelEngine(data_dir=data_dir)

    def plan_from_world(self):
        understanding = self.world.understand_now()
        context = understanding.get("context", {})
        return {
            "mode": context.get("mode", "idle"),
            "signals": context.get("signals", []),
            "recommendation": understanding.get("recommendation"),
            "confidence": 0.85 if context.get("signals") else 0.65,
        }
