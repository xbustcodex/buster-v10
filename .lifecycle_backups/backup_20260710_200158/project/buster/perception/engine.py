from buster.world_model import WorldModelEngine

class PerceptionEngine:
    def __init__(self, data_dir="data"):
        self.world = WorldModelEngine(data_dir=data_dir)

    def perceive_text(self, source, text, context=None, importance=0.5):
        obs = self.world.observe(source=source, summary=text, context=context or {}, importance=importance)
        understanding = self.world.understand_now()
        return {"observation": obs, "understanding": understanding}

    def perceive_camera_observation(self, description, objects=None, scene=None, confidence=0.75):
        context = {"objects": objects or [], "scene": scene or "unknown"}
        return self.world.observe("camera", description, context=context, importance=0.7, confidence=confidence)

    def perceive_desktop_observation(self, active_app, detail=""):
        summary = f"Desktop active app: {active_app}. {detail}".strip()
        return self.world.observe("desktop", summary, context={"active_app": active_app}, importance=0.6)
