from datetime import datetime, timezone

class PerceptionWorldBridge:
    def observation_to_world_event(self, observation):
        kind = observation.get("sound_type") or observation.get("scene") or observation.get("source", "unknown")
        return {
            "type": "perception_observation",
            "kind": kind,
            "source": observation.get("source", "unknown"),
            "importance": observation.get("importance", 0.0),
            "confidence": observation.get("confidence", 0.0),
            "details": observation,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
