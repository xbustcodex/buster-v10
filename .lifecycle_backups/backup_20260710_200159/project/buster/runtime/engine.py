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
