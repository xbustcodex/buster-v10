from __future__ import annotations

from typing import Any, Dict

from .storage import load_json, append_record, now_iso

REFLECTIONS = "data/reflection_journal.json"


class ReflectionCycle:
    """Idle-time maintenance: summarize, compress, and learn from the day."""

    def __init__(self, path: str = REFLECTIONS):
        self.path = path

    def run_daily_reflection(self) -> Dict[str, Any]:
        timeline = load_json("data/mission_timeline_live.json", [])
        experience = load_json("data/experience_memory.json", [])
        skills = load_json("data/skill_profiles.json", {})
        events = timeline[-20:] if isinstance(timeline, list) else []
        reflection = {
            "timestamp": now_iso(),
            "title": "Daily reflection",
            "summary": f"Reviewed {len(events)} recent mission events.",
            "recent_events": events[-8:],
            "skill_snapshot": skills if isinstance(skills, dict) else {},
            "experience_records": len(experience) if isinstance(experience, list) else len(experience.keys()) if isinstance(experience, dict) else 0,
            "recommendations": [],
        }
        if len(events) >= 5:
            reflection["recommendations"].append("Promote repeated successful mission steps into reusable strategies.")
        if reflection["experience_records"] >= 3:
            reflection["recommendations"].append("Review experience records for reusable project templates.")
        append_record(self.path, reflection)
        return reflection
