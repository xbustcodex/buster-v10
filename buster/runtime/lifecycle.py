from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from .storage import load_json, save_json, now
STATE_PATH = Path('data/runtime_lifecycle.json')
class RuntimeLifecycle:
    def __init__(self, path: Path = STATE_PATH):
        self.path = path
        self.state = load_json(path, {'status':'stopped','started_at':None,'stopped_at':None,'starts':0})
    def start(self) -> Dict[str, Any]:
        self.state.update({'status':'running','started_at':now(),'stopped_at':None,'starts':int(self.state.get('starts',0))+1})
        save_json(self.path, self.state); return self.state
    def stop(self) -> Dict[str, Any]:
        self.state.update({'status':'stopped','stopped_at':now()})
        save_json(self.path, self.state); return self.state
    def status(self) -> Dict[str, Any]: return dict(self.state)
