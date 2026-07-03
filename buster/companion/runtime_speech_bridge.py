from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
from buster.runtime.storage import load_json, save_json
QUEUE_PATH = Path('data/proactive_speech_queue.json')
def get_pending_runtime_speech(limit: int = 5) -> List[Dict[str, Any]]:
    items=load_json(QUEUE_PATH, [])
    if not isinstance(items, list): return []
    return [x for x in items if x.get('source') == 'runtime'][-limit:]
def clear_runtime_speech() -> None:
    items=load_json(QUEUE_PATH, [])
    save_json(QUEUE_PATH, [x for x in items if x.get('source') != 'runtime'])
