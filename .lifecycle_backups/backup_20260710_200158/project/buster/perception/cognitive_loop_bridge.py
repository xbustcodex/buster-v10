from __future__ import annotations
from typing import Any, Dict, List
def perception_to_cognitive_observations(perception_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    observations=[]
    for event in perception_events:
        priority=int(event.get('priority',5)); confidence=float(event.get('confidence',0.7))
        if priority>=6 or confidence>=0.8:
            observations.append({'source':event.get('source','perception'), 'type':event.get('type','observation'), 'summary':event.get('summary', event.get('label','Meaningful perception event')), 'priority':priority, 'confidence':confidence, 'raw':event})
    return observations
