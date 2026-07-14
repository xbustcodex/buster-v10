from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from buster.runtime.storage import load_json
def runtime_context_for_planner() -> Dict[str, Any]:
    state=load_json(Path('data/buster_runtime_state.json'), {})
    return {'runtime_tick':state.get('tick_count',0),'runtime_mode':state.get('mode','companion'),'predicted_intent':(state.get('latest_prediction') or {}).get('intent','unknown'),'runtime_privacy_mode':state.get('privacy_mode','unknown')}
