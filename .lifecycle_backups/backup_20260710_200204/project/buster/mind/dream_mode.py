from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import json
DREAM_PATH = Path('data/dream_reflections.json')
def _now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def _load():
    if not DREAM_PATH.exists(): return []
    try: return json.loads(DREAM_PATH.read_text(encoding='utf-8'))
    except Exception: return []
def _save(items):
    DREAM_PATH.parent.mkdir(parents=True, exist_ok=True)
    DREAM_PATH.write_text(json.dumps(items[-300:], indent=2), encoding='utf-8')
class DreamMode:
    def __init__(self): self.reflections = _load()
    def reflect(self, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        context = context or {}; patterns=context.get('patterns', []); goals=context.get('goals', [])
        reflection={'created_at': _now(), 'summary':'Dream mode reviewed recent activity and prepared knowledge for tomorrow.', 'patterns_reviewed':len(patterns), 'goals_reviewed':len(goals), 'recommendations':self._recommend(patterns, goals), 'context':context}
        self.reflections.append(reflection); _save(self.reflections); return reflection
    def _recommend(self, patterns: List[Any], goals: List[Any]) -> List[str]:
        recs=[]
        if len(patterns)>=3: recs.append('Promote repeated patterns into reusable knowledge.')
        if len(goals)>=1: recs.append('Review open goals at next startup.')
        if not recs: recs.append('Continue observing before creating new self-improvement tasks.')
        return recs
    def recent(self, limit:int=10): return self.reflections[-limit:]
