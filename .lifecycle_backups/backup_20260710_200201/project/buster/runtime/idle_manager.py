from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from .storage import load_json, save_json, now
IDLE_PATH = Path('data/runtime_idle_state.json')
class IdleManager:
    def __init__(self, path: Path = IDLE_PATH):
        self.path = path
        self.state = load_json(path, {'idle_ticks':0,'dream_mode_ready':False,'last_activity':None})
    def observe_activity(self, active: bool) -> Dict[str, Any]:
        if active:
            self.state['idle_ticks']=0; self.state['last_activity']=now(); self.state['dream_mode_ready']=False
        else:
            self.state['idle_ticks']=int(self.state.get('idle_ticks',0))+1
            self.state['dream_mode_ready']=self.state['idle_ticks'] >= 5
        save_json(self.path, self.state); return dict(self.state)
