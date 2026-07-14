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
