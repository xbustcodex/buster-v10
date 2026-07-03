from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from buster.runtime.storage import load_json
class RuntimeDashboard:
    def snapshot(self) -> Dict[str, Any]:
        state=load_json(Path('data/buster_runtime_state.json'), {})
        health=load_json(Path('data/runtime_health.json'), {})
        return {'title':'Runtime Integration','status':state.get('runtime_status','unknown'),'tick_count':state.get('tick_count',0),'mode':state.get('mode','companion'),'privacy_mode':state.get('privacy_mode','companion'),'latest_prediction':state.get('latest_prediction',{}),'health':health.get('status','unknown')}
