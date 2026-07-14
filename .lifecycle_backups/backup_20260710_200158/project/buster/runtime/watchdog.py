from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from .storage import load_json, save_json, now
HEALTH_PATH = Path('data/runtime_health.json')
class RuntimeWatchdog:
    def __init__(self, path: Path = HEALTH_PATH):
        self.path = path
        self.health = load_json(path, {'status':'unknown','checks':[]})
    def check(self, state: Dict[str, Any]) -> Dict[str, Any]:
        issues=[]
        if not state.get('enabled', True): issues.append('runtime_disabled')
        if state.get('privacy_mode') == 'off': issues.append('perception_off')
        status = 'healthy' if not issues else 'limited'
        result={'checked_at':now(),'status':status,'issues':issues,'tick':state.get('tick_count',0)}
        self.health={'status':status,'last_check':result,'checks':(self.health.get('checks',[])+[result])[-100:]}
        save_json(self.path, self.health); return result
