try:
    from buster.world_model import WorldModelEngine
except Exception:
    WorldModelEngine = None

class VisionWorldModelBridge:
    def __init__(self, data_dir="data"):
        self.world = WorldModelEngine(data_dir=data_dir) if WorldModelEngine else None

    def record_scene(self, description, objects=None, scene="camera", confidence=0.75):
        if not self.world:
            return {"ok": False, "reason": "WorldModelEngine unavailable"}
        obs = self.world.observe(
            source="camera",
            summary=description,
            context={"objects": objects or [], "scene": scene},
            importance=0.7,
            confidence=confidence,
        )
        return {"ok": True, "observation": obs, "understanding": self.world.understand_now()}
