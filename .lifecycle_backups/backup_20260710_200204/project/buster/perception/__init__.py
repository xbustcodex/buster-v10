"""Buster Perception package public API."""

try:
    from .engine import PerceptionEngine
except Exception:
    class PerceptionEngine:
        def __init__(self, data_dir="data"):
            self.data_dir = data_dir
            self.observations = []

        def observe(self, source="unknown", observation_type="generic", summary="", confidence=1.0, importance=0.5, data=None, **kwargs):
            item = {
                "source": source,
                "observation_type": observation_type,
                "summary": summary,
                "confidence": confidence,
                "importance": importance,
                "data": data or {},
            }
            self.observations.append(item)
            return item

try:
    from .perception_os import PerceptionOS
except Exception:
    PerceptionOS = None

try:
    from .ears import BusterEars
except Exception:
    BusterEars = None

try:
    from .eyes import BusterEyes
except Exception:
    BusterEyes = None

__all__ = ["PerceptionEngine", "PerceptionOS", "BusterEars", "BusterEyes"]
