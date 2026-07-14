from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import json
MISSIONS_PATH = Path('data/self_improvement_missions.json')
def _now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def _load():
    if not MISSIONS_PATH.exists(): return []
    try: return json.loads(MISSIONS_PATH.read_text(encoding='utf-8'))
    except Exception: return []
def _save(items):
    MISSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    MISSIONS_PATH.write_text(json.dumps(items[-300:], indent=2), encoding='utf-8')
class SelfImprovementEngine:
    def __init__(self): self.missions = _load()
    def propose(self, title: str, reason: str, impact: str = 'medium', confidence: float = 0.75) -> Dict[str, Any]:
        mission={'id':'improve_%s_%03d' % (datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S'), len(self.missions)+1), 'created_at':_now(), 'title':title, 'reason':reason, 'impact':impact, 'confidence':round(float(confidence),3), 'status':'proposed', 'requires_user_approval':True}
        self.missions.append(mission); _save(self.missions); return mission
    def analyze_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        counts={}; proposals=[]
        for p in patterns:
            key=str(p.get('name') or p.get('type') or 'unknown'); counts[key]=counts.get(key,0)+1
        for key,count in counts.items():
            if count>=3: proposals.append(self.propose('Create reusable solution for %s' % key, 'Pattern appeared %d times.' % count, 'high', min(0.95,0.65+count*0.05)))
        return proposals
    def list_missions(self, status: str | None = None): return list(self.missions) if status is None else [m for m in self.missions if m.get('status')==status]
