from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = {}

FILES['buster/runtime/__init__.py'] = """
from .engine import BusterRuntimeEngine
from .heartbeat import RuntimeHeartbeat
from .scheduler import RuntimeScheduler
from .dispatcher import RuntimeDispatcher
from .lifecycle import RuntimeLifecycle
from .watchdog import RuntimeWatchdog
from .coordinator import RuntimeCoordinator
from .idle_manager import IdleManager
from .intent_prediction import IntentPredictionEngine
__all__ = ['BusterRuntimeEngine','RuntimeHeartbeat','RuntimeScheduler','RuntimeDispatcher','RuntimeLifecycle','RuntimeWatchdog','RuntimeCoordinator','IdleManager','IntentPredictionEngine']
"""

FILES['buster/runtime/storage.py'] = """
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
DATA_DIR = Path('data')
def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')
def load_json(path: Path, default: Any) -> Any:
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return default
def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
def append_json(path: Path, item: Any, limit: int = 500) -> list:
    items = load_json(path, [])
    if not isinstance(items, list): items = []
    items.append(item)
    items = items[-limit:]
    save_json(path, items)
    return items
"""

FILES['buster/runtime/heartbeat.py'] = """
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict
from .storage import now
@dataclass
class RuntimeHeartbeat:
    tick: int = 0
    mode: str = 'companion'
    interval_seconds: float = 1.0
    created_at: str = ''
    def beat(self) -> Dict[str, Any]:
        self.tick += 1
        self.created_at = now()
        return {'tick': self.tick, 'mode': self.mode, 'timestamp': self.created_at, 'interval_seconds': self.interval_seconds}
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
"""

FILES['buster/runtime/scheduler.py'] = """
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
from .storage import now
class RuntimeScheduler:
    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []
    def add_job(self, name: str, interval_ticks: int, task: Optional[Callable[[], Any]] = None, enabled: bool = True) -> Dict[str, Any]:
        job = {'name': name, 'interval_ticks': max(1, int(interval_ticks)), 'last_tick': 0, 'enabled': enabled, 'created_at': now(), '_task': task}
        self.jobs.append(job)
        return {k:v for k,v in job.items() if k != '_task'}
    def due_jobs(self, tick: int) -> List[Dict[str, Any]]:
        return [job for job in self.jobs if job.get('enabled') and tick - int(job.get('last_tick', 0)) >= int(job.get('interval_ticks', 1))]
    def run_due(self, tick: int) -> List[Dict[str, Any]]:
        results=[]
        for job in self.due_jobs(tick):
            result=None; ok=True
            try:
                if job.get('_task'): result = job['_task']()
            except Exception as exc:
                ok=False; result=str(exc)
            job['last_tick'] = tick
            results.append({'name': job['name'], 'ok': ok, 'result': result, 'ran_at': now()})
        return results
"""

FILES['buster/runtime/dispatcher.py'] = """
from __future__ import annotations
from typing import Any, Callable, Dict, List
from .storage import append_json, now
from pathlib import Path
EVENTS_PATH = Path('data/runtime_events.json')
class RuntimeDispatcher:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = {}
    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        self.subscribers.setdefault(event_type, []).append(handler)
    def publish(self, event_type: str, payload: Dict[str, Any] | None = None, source: str = 'runtime') -> Dict[str, Any]:
        event={'type': event_type, 'source': source, 'payload': payload or {}, 'created_at': now()}
        append_json(EVENTS_PATH, event, limit=1000)
        for handler in self.subscribers.get(event_type, []) + self.subscribers.get('*', []):
            try: handler(event)
            except Exception: pass
        return event
"""

FILES['buster/runtime/lifecycle.py'] = """
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
"""

FILES['buster/runtime/watchdog.py'] = """
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
"""

FILES['buster/runtime/idle_manager.py'] = """
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from .storage import load_json, save_json, now
IDLE_PATH = Path('data/runtime_idle_state.json')
class IdleManager:
    def __init__(self, path: Path = IDLE_PATH):
        self.path = path
        self.state = load_json(path, {'idle_ticks':0,'dream_mode_ready':False,'last_activity':None})
    def observe_activity(self, active: bool) -> Dict[str, Any]:
        if active:
            self.state['idle_ticks']=0; self.state['last_activity']=now(); self.state['dream_mode_ready']=False
        else:
            self.state['idle_ticks']=int(self.state.get('idle_ticks',0))+1
            self.state['dream_mode_ready']=self.state['idle_ticks'] >= 5
        save_json(self.path, self.state); return dict(self.state)
"""

FILES['buster/runtime/intent_prediction.py'] = """
from __future__ import annotations
from typing import Any, Dict, List
from .storage import append_json, now
from pathlib import Path
PREDICTIONS_PATH = Path('data/intent_predictions.json')
class IntentPredictionEngine:
    def predict(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        text=' '.join(str(o.get('summary','')) + ' ' + str(o.get('type','')) for o in observations).lower()
        intent='general_work'; confidence=0.55; actions=[]
        if 'android studio' in text or 'pixel' in text or 'logcat' in text:
            intent='android_development'; confidence=0.88; actions=['prepare_android_plugin','monitor_logcat','index_current_project']
        elif 'esp32' in text or 'arduino' in text or 'serial' in text:
            intent='embedded_development'; confidence=0.86; actions=['prepare_arduino_plugin','monitor_serial','load_hardware_context']
        elif 'python' in text or 'tkinter' in text:
            intent='python_development'; confidence=0.82; actions=['prepare_python_tools','run_tests_when_safe']
        prediction={'intent':intent,'confidence':confidence,'suggested_actions':actions,'created_at':now(),'observations':observations[-5:]}
        append_json(PREDICTIONS_PATH, prediction, limit=300)
        return prediction
"""

FILES['buster/runtime/coordinator.py'] = """
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
from .storage import load_json, save_json, now
COORD_PATH = Path('data/runtime_coordination_state.json')
class RuntimeCoordinator:
    def __init__(self, path: Path = COORD_PATH):
        self.path = path
        self.state = load_json(path, {'last_sync':None,'modules':{}})
    def sync(self, heartbeat: Dict[str, Any], observations: List[Dict[str, Any]], prediction: Dict[str, Any]) -> Dict[str, Any]:
        self.state['last_sync']=now()
        self.state['heartbeat']=heartbeat
        self.state['latest_prediction']=prediction
        self.state['observation_count']=len(observations)
        self.state.setdefault('modules', {}).update({'perception':'connected','world_model':'connected','mind':'connected','companion':'connected','mission_control':'connected'})
        save_json(self.path, self.state); return dict(self.state)
"""

FILES['buster/runtime/engine.py'] = """
from __future__ import annotations
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from .storage import load_json, save_json, append_json, now
from .heartbeat import RuntimeHeartbeat
from .scheduler import RuntimeScheduler
from .dispatcher import RuntimeDispatcher
from .lifecycle import RuntimeLifecycle
from .watchdog import RuntimeWatchdog
from .coordinator import RuntimeCoordinator
from .idle_manager import IdleManager
from .intent_prediction import IntentPredictionEngine
STATE_PATH = Path('data/buster_runtime_state.json')
MISSION_PATH = Path('data/mission_control_unified.json')
SPEECH_PATH = Path('data/proactive_speech_queue.json')
class BusterRuntimeEngine:
    def __init__(self, observation_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None):
        self.state = load_json(STATE_PATH, {'enabled':True,'tick_count':0,'mode':'companion','privacy_mode':'companion','last_tick':None})
        self.observation_provider = observation_provider or (lambda: [])
        self.heartbeat = RuntimeHeartbeat(tick=int(self.state.get('tick_count',0)), mode=self.state.get('mode','companion'))
        self.scheduler = RuntimeScheduler()
        self.dispatcher = RuntimeDispatcher()
        self.lifecycle = RuntimeLifecycle()
        self.watchdog = RuntimeWatchdog()
        self.coordinator = RuntimeCoordinator()
        self.idle = IdleManager()
        self.predictor = IntentPredictionEngine()
        self.scheduler.add_job('watchdog_check', 3, lambda: self.watchdog.check(self.state))
        self.scheduler.add_job('mission_control_sync', 1, lambda: self._write_mission_status())
    def start(self) -> Dict[str, Any]:
        life=self.lifecycle.start(); self.state['enabled']=True; self.state['runtime_status']='running'; self.state['started_at']=life.get('started_at'); self._save(); return self.state
    def stop(self) -> Dict[str, Any]:
        life=self.lifecycle.stop(); self.state['runtime_status']='stopped'; self.state['stopped_at']=life.get('stopped_at'); self._save(); return self.state
    def _save(self) -> None: save_json(STATE_PATH, self.state)
    def tick_once(self, observations: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        observations = observations if observations is not None else self.observation_provider()
        if self.state.get('privacy_mode') == 'off': observations=[]
        hb = self.heartbeat.beat(); self.state['tick_count']=hb['tick']; self.state['last_tick']=hb['timestamp']
        prediction = self.predictor.predict(observations) if observations else {'intent':'idle','confidence':0.5,'suggested_actions':[],'created_at':now()}
        active = bool(observations) or prediction.get('intent') not in {'idle','general_work'}
        idle_state = self.idle.observe_activity(active)
        coordination = self.coordinator.sync(hb, observations, prediction)
        jobs = self.scheduler.run_due(hb['tick'])
        event = self.dispatcher.publish('runtime.tick', {'heartbeat':hb,'prediction':prediction,'observations':observations,'jobs':jobs}, source='runtime')
        speech = self._maybe_queue_speech(prediction, observations)
        self.state.update({'latest_prediction':prediction,'idle':idle_state,'last_event':event,'last_jobs':jobs,'last_speech':speech,'coordination':coordination})
        self._write_mission_status(); self._save()
        return {'state':self.state,'heartbeat':hb,'prediction':prediction,'jobs':jobs,'speech':speech}
    def _maybe_queue_speech(self, prediction: Dict[str, Any], observations: List[Dict[str, Any]]):
        if self.state.get('mode') == 'silent': return None
        if prediction.get('confidence',0) < 0.8: return None
        intent=prediction.get('intent')
        message=None
        if intent == 'android_development': message='I think you are starting Android development. I can prepare Logcat and the Android plugin.'
        elif intent == 'embedded_development': message='ESP32 or Arduino work detected. I can prepare the serial monitor and hardware context.'
        elif intent == 'python_development': message='Python development detected. I can keep tests and repository context ready.'
        if not message: return None
        item={'created_at':now(),'source':'runtime','intent':intent,'message':message,'confidence':prediction.get('confidence')}
        append_json(SPEECH_PATH, item, limit=300); return item
    def _write_mission_status(self) -> Dict[str, Any]:
        status={'updated_at':now(),'runtime':'running' if self.state.get('enabled',True) else 'disabled','tick_count':self.state.get('tick_count',0),'mode':self.state.get('mode','companion'),'privacy_mode':self.state.get('privacy_mode','companion'),'latest_prediction':self.state.get('latest_prediction'),'summary':'Buster runtime heartbeat is active.'}
        save_json(MISSION_PATH, status); return status
    def status(self) -> Dict[str, Any]: return dict(self.state)
"""

FILES['buster/workspace/runtime_dashboard.py'] = """
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from buster.runtime.storage import load_json
class RuntimeDashboard:
    def snapshot(self) -> Dict[str, Any]:
        state=load_json(Path('data/buster_runtime_state.json'), {})
        health=load_json(Path('data/runtime_health.json'), {})
        return {'title':'Runtime Integration','status':state.get('runtime_status','unknown'),'tick_count':state.get('tick_count',0),'mode':state.get('mode','companion'),'privacy_mode':state.get('privacy_mode','companion'),'latest_prediction':state.get('latest_prediction',{}),'health':health.get('status','unknown')}
"""

FILES['buster/ui/widgets/runtime_widget.py'] = """
from __future__ import annotations
from buster.workspace.runtime_dashboard import RuntimeDashboard
class RuntimeWidgetModel:
    def build(self):
        snap=RuntimeDashboard().snapshot()
        return {'heading':'Buster Runtime','lines':['Status: %s' % snap.get('status'),'Ticks: %s' % snap.get('tick_count'),'Mode: %s' % snap.get('mode'),'Health: %s' % snap.get('health')], 'snapshot': snap}
"""

FILES['buster/brain/planner/runtime_planner_bridge.py'] = """
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from buster.runtime.storage import load_json
def runtime_context_for_planner() -> Dict[str, Any]:
    state=load_json(Path('data/buster_runtime_state.json'), {})
    return {'runtime_tick':state.get('tick_count',0),'runtime_mode':state.get('mode','companion'),'predicted_intent':(state.get('latest_prediction') or {}).get('intent','unknown'),'runtime_privacy_mode':state.get('privacy_mode','unknown')}
"""

FILES['buster/companion/runtime_speech_bridge.py'] = """
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
"""

FILES['BUSTER_RUNTIME_INTEGRATION.md'] = """
# Buster v5.6 Runtime Integration

The runtime layer is the nervous system of Buster AI OS.

It connects perception, world model, cognitive loop, mission control, companion speech, scheduler jobs, privacy modes, and intent prediction into a safe continuous heartbeat.

## Runtime rules

1. Keep the heartbeat lightweight.
2. Respect privacy modes before processing observations.
3. Speak only when events are meaningful and confidence is high.
4. Feed status into Mission Control every tick.
5. Let background jobs run through the scheduler, not random loops.

## Next direction

v6.0 should focus on making Buster start with Windows, open Mission Control, load memory, start the heartbeat, and behave like a real desktop AI operating companion.
"""

DATA_DEFAULTS = {
    'data/buster_runtime_state.json': {'enabled': True, 'runtime_status': 'installed', 'tick_count': 0, 'mode': 'companion', 'privacy_mode': 'companion'},
    'data/runtime_events.json': [],
    'data/runtime_health.json': {'status': 'installed', 'checks': []},
    'data/runtime_lifecycle.json': {'status': 'stopped', 'started_at': None, 'stopped_at': None, 'starts': 0},
    'data/runtime_idle_state.json': {'idle_ticks': 0, 'dream_mode_ready': False, 'last_activity': None},
    'data/runtime_coordination_state.json': {'last_sync': None, 'modules': {}},
    'data/intent_predictions.json': [],
}

def write_file(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.strip() + '\n', encoding='utf-8')
    print('[WRITE]', path)

def create_json(path: str, data) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print('[SKIP]', path)
        return
    target.write_text(json.dumps(data, indent=2), encoding='utf-8')
    print('[CREATE]', path)

def main():
    print('=== Applying Buster v5.6 Runtime Integration Patch ===')
    for path, content in FILES.items():
        write_file(path, content)
    for path, data in DATA_DEFAULTS.items():
        create_json(path, data)
    print('\nSUCCESS: Buster v5.6 Runtime Integration installed.')
    print('Next: python test_v5_6_runtime_integration.py')
if __name__ == '__main__':
    main()
