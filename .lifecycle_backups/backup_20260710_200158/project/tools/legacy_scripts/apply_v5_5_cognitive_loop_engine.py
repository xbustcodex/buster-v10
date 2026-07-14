from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = {}

FILES['buster/mind/cognitive_loop.py'] = '''
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

DATA_DIR = Path('data')
STATE_PATH = DATA_DIR / 'cognitive_loop_state.json'
THOUGHTS_PATH = DATA_DIR / 'internal_thoughts.json'

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default

def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')

@dataclass
class CognitiveStep:
    phase: str
    summary: str
    confidence: float = 0.75
    priority: int = 5
    source: str = 'cognitive_loop'
    metadata: Optional[Dict[str, Any]] = None
    created_at: str = ''
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if not data['created_at']:
            data['created_at'] = _now()
        if data['metadata'] is None:
            data['metadata'] = {}
        return data

class CognitiveLoopEngine:
    PHASES = ['perceive','attend','think','update_world_model','update_working_memory','review_goals','plan','act','learn','reflect','companion']
    def __init__(self, state_path: Path = STATE_PATH, thoughts_path: Path = THOUGHTS_PATH):
        self.state_path = state_path
        self.thoughts_path = thoughts_path
        self.state = _load_json(state_path, self._default_state())
        self.thoughts: List[Dict[str, Any]] = _load_json(thoughts_path, [])
    def _default_state(self) -> Dict[str, Any]:
        return {'enabled': True, 'mode': 'companion', 'tick_count': 0, 'current_phase': 'idle', 'last_tick': None, 'last_summary': 'Cognitive loop ready.', 'heartbeat_seconds': 5, 'dream_mode_enabled': True, 'internal_dialogue_enabled': True, 'self_improvement_enabled': True}
    def save(self) -> None:
        _save_json(self.state_path, self.state)
        _save_json(self.thoughts_path, self.thoughts[-500:])
    def set_mode(self, mode: str) -> Dict[str, Any]:
        if mode not in {'silent','assistant','companion','engineer','development'}:
            raise ValueError('Unknown cognitive loop mode: %s' % mode)
        self.state['mode'] = mode
        self.state['updated_at'] = _now()
        self.save()
        return self.state
    def create_thought(self, observation: str, meaning: str, proposed_action: str = '', confidence: float = 0.75, source: str = 'mind') -> Dict[str, Any]:
        thought = {'id': 'thought_%s_%03d' % (datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S'), len(self.thoughts)+1), 'created_at': _now(), 'source': source, 'observation': observation, 'meaning': meaning, 'proposed_action': proposed_action, 'confidence': round(float(confidence), 3), 'status': 'open'}
        self.thoughts.append(thought)
        self.save()
        return thought
    def tick(self, observations: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        observations = observations or []
        self.state['tick_count'] = int(self.state.get('tick_count', 0)) + 1
        self.state['last_tick'] = _now()
        phase = self.PHASES[self.state['tick_count'] % len(self.PHASES)]
        self.state['current_phase'] = phase
        summary = self._summarize_phase(phase, observations)
        self.state['last_summary'] = summary
        step = CognitiveStep(phase=phase, summary=summary, confidence=0.8 if observations else 0.65, priority=8 if observations else 4, metadata={'observations': observations[:5]}).to_dict()
        self.state.setdefault('recent_steps', []).append(step)
        self.state['recent_steps'] = self.state['recent_steps'][-100:]
        if observations:
            top = observations[0]
            self.create_thought(str(top.get('summary') or top.get('type') or 'observation'), 'Buster noticed a meaningful change in the environment.', 'Update working memory and review active goals.', float(top.get('confidence', 0.75)), str(top.get('source', 'perception')))
        self.save()
        return {'state': self.state, 'step': step, 'thoughts': self.thoughts[-5:]}
    def _summarize_phase(self, phase: str, observations: List[Dict[str, Any]]) -> str:
        if observations:
            return '%s processed %d meaningful observation(s).' % (phase.replace('_',' ').title(), len(observations))
        messages = {'perceive':'Checking senses for new information.','attend':'Deciding what deserves focus.','think':'Reviewing current context.','update_world_model':'Keeping the world model current.','update_working_memory':'Refreshing active mission context.','review_goals':'Checking active goals and priorities.','plan':'Looking for useful next actions.','act':'No safe autonomous action required right now.','learn':'Checking whether new patterns can be learned.','reflect':'Preparing knowledge for later reflection.','companion':'Companion mode is present and quiet.'}
        return messages.get(phase, 'Cognitive loop heartbeat.')
    def status(self) -> Dict[str, Any]:
        return dict(self.state)
'''

FILES['buster/mind/internal_dialogue.py'] = '''
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
'''

FILES['buster/mind/dream_mode.py'] = '''
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
'''

FILES['buster/mind/self_improvement.py'] = '''
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
'''

FILES['buster/mind/continuous_runtime.py'] = '''
from __future__ import annotations
import threading, time
from typing import Callable, Dict, Any, List, Optional
from .cognitive_loop import CognitiveLoopEngine
ObservationProvider = Callable[[], List[Dict[str, Any]]]
class ContinuousMindRuntime:
    def __init__(self, loop: CognitiveLoopEngine | None = None, provider: ObservationProvider | None = None, interval: float = 5.0):
        self.loop=loop or CognitiveLoopEngine(); self.provider=provider or (lambda: []); self.interval=float(interval); self._running=False; self._thread: Optional[threading.Thread]=None
    def tick_once(self): return self.loop.tick(self.provider() or [])
    def start(self):
        if self._running: return
        self._running=True; self._thread=threading.Thread(target=self._run, name='BusterContinuousMind', daemon=True); self._thread.start()
    def _run(self):
        while self._running:
            try: self.tick_once()
            except Exception: pass
            time.sleep(self.interval)
    def stop(self):
        self._running=False
        if self._thread and self._thread.is_alive(): self._thread.join(timeout=2.0)
    def is_running(self): return self._running
'''

FILES['buster/perception/cognitive_loop_bridge.py'] = '''
from __future__ import annotations
from typing import Any, Dict, List
def perception_to_cognitive_observations(perception_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    observations=[]
    for event in perception_events:
        priority=int(event.get('priority',5)); confidence=float(event.get('confidence',0.7))
        if priority>=6 or confidence>=0.8:
            observations.append({'source':event.get('source','perception'), 'type':event.get('type','observation'), 'summary':event.get('summary', event.get('label','Meaningful perception event')), 'priority':priority, 'confidence':confidence, 'raw':event})
    return observations
'''

FILES['buster/workspace/cognitive_loop_dashboard.py'] = '''
from __future__ import annotations
from typing import Any, Dict
from buster.mind.cognitive_loop import CognitiveLoopEngine
from buster.mind.internal_dialogue import InternalDialogue
from buster.mind.dream_mode import DreamMode
class CognitiveLoopDashboard:
    def snapshot(self) -> Dict[str, Any]:
        state=CognitiveLoopEngine().status(); dialogue=InternalDialogue(); dream=DreamMode()
        return {'title':'Cognitive Loop','enabled':state.get('enabled',False),'mode':state.get('mode','unknown'),'phase':state.get('current_phase','unknown'),'tick_count':state.get('tick_count',0),'last_summary':state.get('last_summary',''),'recent_steps':state.get('recent_steps',[])[-10:],'internal_dialogue':dialogue.recent(10),'dream_reflections':dream.recent(5)}
'''

FILES['buster/ui/widgets/cognitive_loop_widget.py'] = '''
from __future__ import annotations
from typing import Any, Dict
class CognitiveLoopWidgetModel:
    def __init__(self, data: Dict[str, Any] | None = None): self.data=data or {}
    def as_cards(self):
        return [{'label':'Mode','value':self.data.get('mode','unknown')},{'label':'Phase','value':self.data.get('phase','unknown')},{'label':'Ticks','value':self.data.get('tick_count',0)},{'label':'Last Thought','value':self.data.get('last_summary','')}]
'''

FILES['buster/brain/planner/cognitive_loop_planner_bridge.py'] = '''
from __future__ import annotations
from typing import Any, Dict
def cognitive_loop_context_for_planner(loop_state: Dict[str, Any]) -> Dict[str, Any]:
    phase=loop_state.get('current_phase','idle')
    return {'cognitive_phase':phase,'loop_enabled':loop_state.get('enabled',True),'mode':loop_state.get('mode','companion'),'last_summary':loop_state.get('last_summary',''),'should_plan':phase in {'plan','review_goals','act'},'should_reflect':phase in {'learn','reflect'}}
'''

FILES['buster/mind/__init__.py'] = '''
from .cognitive_loop import CognitiveLoopEngine, CognitiveStep
from .internal_dialogue import InternalDialogue
from .dream_mode import DreamMode
from .self_improvement import SelfImprovementEngine
from .continuous_runtime import ContinuousMindRuntime
__all__=['CognitiveLoopEngine','CognitiveStep','InternalDialogue','DreamMode','SelfImprovementEngine','ContinuousMindRuntime']
'''

FILES['BUSTER_COGNITIVE_LOOP.md'] = '''# Buster Cognitive Loop

Buster v5.5 introduces a continuous cognitive heartbeat.

Loop: perceive → attend → think → update world model → update working memory → review goals → plan → act → learn → reflect → companion.

Major parts:
- cognitive loop heartbeat
- internal thoughts
- internal agent dialogue
- dream/reflection mode
- self-improvement mission proposals
- perception bridge

Self-improvement missions are proposals by default and require user approval.
'''

TEST = '''
from pathlib import Path
from buster.mind.cognitive_loop import CognitiveLoopEngine
from buster.mind.internal_dialogue import InternalDialogue
from buster.mind.dream_mode import DreamMode
from buster.mind.self_improvement import SelfImprovementEngine
from buster.mind.continuous_runtime import ContinuousMindRuntime
from buster.perception.cognitive_loop_bridge import perception_to_cognitive_observations
from buster.brain.planner.cognitive_loop_planner_bridge import cognitive_loop_context_for_planner
from buster.workspace.cognitive_loop_dashboard import CognitiveLoopDashboard

def main():
    loop=CognitiveLoopEngine()
    result=loop.tick([{'source':'test','type':'wake_word','summary':'Buster heard his name','priority':9,'confidence':0.95}])
    assert result['state']['tick_count'] >= 1
    assert result['thoughts']
    dialogue=InternalDialogue(); msg=dialogue.say('Planner','I am reviewing the goal loop.',target='Builder',confidence=0.9)
    assert msg['agent']=='Planner' and dialogue.recent(1)[0]['target']=='Builder'
    dream=DreamMode(); reflection=dream.reflect({'patterns':[{'name':'tkinter_layout'}]*3,'goals':[{'title':'Improve UI'}]})
    assert reflection['recommendations']
    improver=SelfImprovementEngine(); proposals=improver.analyze_patterns([{'name':'import_fix'},{'name':'import_fix'},{'name':'import_fix'}])
    assert proposals and proposals[0]['requires_user_approval'] is True
    observations=perception_to_cognitive_observations([{'source':'ears','type':'speech','summary':'User said Buster','priority':9,'confidence':0.92},{'source':'ambient','type':'fan','summary':'Fan noise','priority':2,'confidence':0.4}])
    assert len(observations)==1
    runtime=ContinuousMindRuntime(provider=lambda: observations, interval=0.01); once=runtime.tick_once(); assert 'state' in once
    planner_context=cognitive_loop_context_for_planner(loop.status()); assert 'cognitive_phase' in planner_context
    dash=CognitiveLoopDashboard().snapshot(); assert dash['title']=='Cognitive Loop'
    for path in ['data/cognitive_loop_state.json','data/internal_thoughts.json','data/internal_dialogue.json','data/dream_reflections.json','data/self_improvement_missions.json']:
        assert Path(path).exists(), path
    print('SUCCESS: v5.5 Cognitive Loop Engine tests passed')
if __name__=='__main__': main()
'''

def write_file(path, content):
    target=ROOT/path; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(content.lstrip('\n'), encoding='utf-8'); print(f'[WRITE] {path}')
def create_json(path, default):
    target=ROOT/path; target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists(): print(f'[SKIP] {path}'); return
    target.write_text(json.dumps(default, indent=2), encoding='utf-8'); print(f'[CREATE] {path}')
def main():
    print('=== Applying Buster v5.5 Cognitive Loop Engine Patch ===')
    for path, content in FILES.items(): write_file(path, content)
    write_file('test_v5_5_cognitive_loop_engine.py', TEST)
    create_json('data/cognitive_loop_state.json', {'enabled':True,'mode':'companion','tick_count':0,'current_phase':'idle','last_summary':'Cognitive loop ready.','heartbeat_seconds':5,'dream_mode_enabled':True,'internal_dialogue_enabled':True,'self_improvement_enabled':True})
    for path, default in [('data/internal_thoughts.json', []),('data/internal_dialogue.json', []),('data/dream_reflections.json', []),('data/self_improvement_missions.json', []),('data/cognitive_runtime_state.json', {'running':False,'mode':'manual'})]: create_json(path, default)
    print('\nSUCCESS: Buster v5.5 Cognitive Loop Engine installed.')
    print('Next: python test_v5_5_cognitive_loop_engine.py')
if __name__=='__main__': main()
