from buster.utils.datetime_utils import utc_now, utc_timestamp
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .mission_metrics import MissionMetrics
from .mission_status import MissionStatus, MissionTimeline


class MissionControlDashboard:
    """Unified AI OS status view for Buster.

    Mission Control pulls together autonomy, intelligence, learning,
    experience, plugins, skills, events, agents and jobs into one snapshot.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metrics = MissionMetrics(data_dir=str(self.data_dir))
        self.timeline = MissionTimeline()
        self.state_path = self.data_dir / "mission_control_dashboard.json"

    def snapshot(self) -> Dict[str, Any]:
        metrics = self.metrics.collect()
        status = MissionStatus(
            confidence=float(metrics.get("confidence") or 0.0),
            risk=str(metrics.get("risk") or "unknown"),
            active_agents=int(metrics.get("active_agents") or 0),
            running_jobs=int(metrics.get("running_jobs") or 0),
            plugins_loaded=int(metrics.get("plugins_loaded") or 0),
            learning_entries=int(metrics.get("learning_entries") or 0),
            experience_entries=int(metrics.get("experience_entries") or 0),
            skills_tracked=int(metrics.get("skills_tracked") or 0),
            last_updated=utc_now().replace(tzinfo=None).isoformat(timespec="seconds"),
        ).to_dict()

        health = self.system_health(status)
        snapshot = {
            "version": "3.9",
            "title": "Buster Mission Control",
            "status": status,
            "metrics": metrics,
            "health": health,
            "timeline": self.timeline.latest(20),
        }
        self.save(snapshot)
        return snapshot

    def system_health(self, status: Dict[str, Any]) -> str:
        confidence = float(status.get("confidence") or 0.0)
        risk = str(status.get("risk") or "unknown").lower()
        if confidence >= 0.85 and risk in ("low", "safe", "unknown"):
            return "GOOD"
        if confidence >= 0.55 and risk not in ("critical", "high"):
            return "WATCH"
        return "CAUTION"

    def record_event(self, event_type: str, message: str, source: str = "mission_control") -> Dict[str, Any]:
        item = self.timeline.add(event_type, message, source)
        try:
            path = self.data_dir / "mission_timeline.json"
            existing = []
            if path.exists():
                existing = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
            existing.append(item)
            path.write_text(json.dumps(existing[-200:], indent=2), encoding="utf-8")
        except Exception:
            pass
        return item

    def save(self, snapshot: Dict[str, Any]) -> None:
        self.state_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    def render_text(self) -> str:
        snap = self.snapshot()
        s = snap["status"]
        return "\n".join([
            "=" * 54,
            "BUSTER MISSION CONTROL",
            "=" * 54,
            f"Mode: {s['mode']}  Health: {snap['health']}  Confidence: {s['confidence']}",
            f"Risk: {s['risk']}",
            f"Agents: {s['active_agents']}  Jobs: {s['running_jobs']}  Plugins: {s['plugins_loaded']}",
            f"Learning: {s['learning_entries']}  Experience: {s['experience_entries']}  Skills: {s['skills_tracked']}",
            f"Updated: {s['last_updated']}",
            "=" * 54,
        ])
