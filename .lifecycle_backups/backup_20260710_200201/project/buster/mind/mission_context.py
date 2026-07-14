from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

@dataclass
class MissionContext:
    mission_id: str
    title: str
    status: str = "active"
    priority: int = 5
    confidence: float = 0.75
    risk: str = "medium"
    active_goal_ids: List[str] = None
    current_focus: str = ""
    notes: List[str] = None
    updated_at: str = ""

    def __post_init__(self):
        if self.active_goal_ids is None:
            self.active_goal_ids = []
        if self.notes is None:
            self.notes = []
        if not self.updated_at:
            self.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class MissionContextManager:
    def __init__(self):
        self.current: Optional[MissionContext] = None

    def start(self, title: str, mission_id: Optional[str] = None, priority: int = 5) -> MissionContext:
        mission_id = mission_id or "mission_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.current = MissionContext(mission_id=mission_id, title=title, priority=priority)
        return self.current

    def attach_goal(self, goal_id: str) -> None:
        if not self.current:
            self.start("General mission")
        if goal_id not in self.current.active_goal_ids:
            self.current.active_goal_ids.append(goal_id)
            self.touch()

    def set_focus(self, focus: str) -> None:
        if not self.current:
            self.start("General mission")
        self.current.current_focus = focus
        self.touch()

    def note(self, message: str) -> None:
        if not self.current:
            self.start("General mission")
        self.current.notes.append(message)
        self.touch()

    def touch(self) -> None:
        if self.current:
            self.current.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def snapshot(self) -> Dict[str, Any]:
        return self.current.to_dict() if self.current else {}
