class AttentionSystem:
    def choose_focus(self, observations):
        if not observations:
            return {"focus": "idle", "reason": "No observations", "importance": 0.0}
        ranked = sorted(observations, key=lambda o: float(o.get("importance", 0.0)), reverse=True)
        top = ranked[0]
        focus = top.get("sound_type") or top.get("scene") or top.get("source", "unknown")
        reason = "Wake word detected" if "buster" in str(top.get("text", "")).lower() else "Highest importance observation"
        return {"focus": focus, "reason": reason, "importance": float(top.get("importance", 0.0)), "observation": top}
