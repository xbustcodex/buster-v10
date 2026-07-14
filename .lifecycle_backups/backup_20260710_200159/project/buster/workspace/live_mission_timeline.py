from __future__ import annotations
from typing import Any, Dict
from buster.living.live_timeline import LiveMissionTimeline
from buster.living.event_bridge import MissionTimelineEventBridge

class LiveMissionTimelineView:
    """Mission Control view model for the live timeline."""
    def __init__(self):
        self.timeline = LiveMissionTimeline()
        self.bridge = MissionTimelineEventBridge(self.timeline)
    def record_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        return self.bridge.handle(event)
    def get_view_model(self, count: int = 25) -> Dict[str, Any]:
        events = self.timeline.recent(count)
        return {"title": "Live Mission Timeline", "count": len(events), "events": events, "lines": [self.timeline.line_for(e) for e in events]}
