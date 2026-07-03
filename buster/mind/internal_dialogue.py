from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import json
DIALOGUE_PATH = Path('data/internal_dialogue.json')
def _now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def _load():
    if not DIALOGUE_PATH.exists(): return []
    try: return json.loads(DIALOGUE_PATH.read_text(encoding='utf-8'))
    except Exception: return []
def _save(items):
    DIALOGUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DIALOGUE_PATH.write_text(json.dumps(items[-500:], indent=2), encoding='utf-8')
class InternalDialogue:
    def __init__(self): self.items = _load()
    def say(self, agent: str, message: str, target: str = 'all', mission_id: str = 'current', confidence: float = 0.75) -> Dict[str, Any]:
        item = {'created_at': _now(), 'mission_id': mission_id, 'agent': agent, 'target': target, 'message': message, 'confidence': round(float(confidence), 3)}
        self.items.append(item); _save(self.items); return item
    def recent(self, limit: int = 20) -> List[Dict[str, Any]]: return self.items[-limit:]
    def clear(self): self.items=[]; _save(self.items)
