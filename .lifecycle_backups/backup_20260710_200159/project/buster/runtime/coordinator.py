from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
from .storage import load_json, save_json, now
COORD_PATH = Path('data/runtime_coordination_state.json')
class RuntimeCoordinator:
    def __init__(self, path: Path = COORD_PATH):
        self.path = path
        self.state = load_json(path, {'last_sync':None,'modules':{}})
    def sync(self, heartbeat: Dict[str, Any], observations: List[Dict[str, Any]], prediction: Dict[str, Any]) -> Dict[str, Any]:
        self.state['last_sync']=now()
        self.state['heartbeat']=heartbeat
        self.state['latest_prediction']=prediction
        self.state['observation_count']=len(observations)
        self.state.setdefault('modules', {}).update({'perception':'connected','world_model':'connected','mind':'connected','companion':'connected','mission_control':'connected'})
        save_json(self.path, self.state); return dict(self.state)
