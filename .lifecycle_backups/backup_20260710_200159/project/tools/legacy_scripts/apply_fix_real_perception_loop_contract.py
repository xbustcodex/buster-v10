from pathlib import Path

print('=== Applying RealPerceptionLoop Contract Repair ===')

path = Path('buster/perception/real_perception_loop.py')
path.parent.mkdir(parents=True, exist_ok=True)

code = r'''from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


@dataclass
class PerceptionObservation:
    source: str
    observation_type: str
    summary: str
    confidence: float = 0.5
    importance: float = 0.5
    data: Dict[str, Any] | None = None
    timestamp: str = ''

    def to_dict(self) -> Dict[str, Any]:
        item = asdict(self)
        if not item.get('timestamp'):
            item['timestamp'] = _now()
        if item.get('data') is None:
            item['data'] = {}
        return item


class RealPerceptionLoop:
    """v5.1 real perception loop compatibility layer.

    This class accepts observations from screen/camera/audio/project feeds,
    stores them locally, and returns a stable contract used by v5.1+ tests
    and later runtime/doctor tools.
    """

    def __init__(self, data_dir: str | Path = 'data', auto_persist: bool = True) -> None:
        self.data_dir = Path(data_dir)
        self.auto_persist = auto_persist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.data_dir / 'real_perception_loop_state.json'
        self.observations_path = self.data_dir / 'real_perception_loop_observations.json'
        self.observations: List[Dict[str, Any]] = self._load_observations()
        self.state: Dict[str, Any] = self._load_state()

    def _load_json(self, path: Path, default: Any) -> Any:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return default
        return default

    def _write_json(self, path: Path, value: Any) -> None:
        if not self.auto_persist:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2), encoding='utf-8')

    def _load_observations(self) -> List[Dict[str, Any]]:
        data = self._load_json(self.observations_path, [])
        return data if isinstance(data, list) else []

    def _load_state(self) -> Dict[str, Any]:
        data = self._load_json(self.state_path, {})
        if not isinstance(data, dict):
            data = {}
        data.setdefault('status', 'ready')
        data.setdefault('world_observations', len(self.observations))
        data.setdefault('working_memory_updates', 0)
        data.setdefault('companion_updates', 0)
        data.setdefault('last_observation', None)
        return data

    def observe(
        self,
        source: str = 'unknown',
        observation_type: str = 'observation',
        summary: str = '',
        confidence: float = 0.5,
        importance: float = 0.5,
        data: Optional[Dict[str, Any]] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        observation = PerceptionObservation(
            source=source,
            observation_type=observation_type,
            summary=summary,
            confidence=float(confidence),
            importance=float(importance),
            data=data or {},
            timestamp=_now(),
        ).to_dict()
        if extra:
            observation['extra'] = extra

        self.observations.append(observation)
        self.state['status'] = 'observing'
        self.state['last_observation'] = observation
        self.state['world_observations'] = len(self.observations)
        self.state['working_memory_updates'] = int(self.state.get('working_memory_updates', 0)) + 1
        self.state['companion_updates'] = int(self.state.get('companion_updates', 0)) + (1 if importance >= 0.6 else 0)
        self.state['updated'] = _now()

        world_update = {
            'world_observations': len(self.observations),
            'last_source': source,
            'last_type': observation_type,
            'updated': self.state['updated'],
        }
        working_memory_update = {
            'working_memory_items': self.state['working_memory_updates'],
            'active_context': summary,
            'importance': float(importance),
        }
        companion_update = {
            'should_speak': bool(importance >= 0.85 and confidence >= 0.7),
            'message': summary if importance >= 0.85 and confidence >= 0.7 else '',
            'companion_updates': self.state['companion_updates'],
        }

        self._write_json(self.observations_path, self.observations)
        self._write_json(self.state_path, self.state)

        return {
            'ok': True,
            'observation': observation,
            'world_update': world_update,
            'working_memory_update': working_memory_update,
            'companion_update': companion_update,
            'state': dict(self.state),
        }

    def observe_many(self, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.observe(**item) for item in observations]

    def snapshot(self) -> Dict[str, Any]:
        return {
            'state': dict(self.state),
            'observations': list(self.observations),
            'count': len(self.observations),
        }

    def tick(self) -> Dict[str, Any]:
        self.state['status'] = 'idle'
        self.state['updated'] = _now()
        self._write_json(self.state_path, self.state)
        return {'ok': True, 'state': dict(self.state)}
'''

path.write_text(code, encoding='utf-8')
print(f'[WRITE] {path}')
print('\nSUCCESS: RealPerceptionLoop contract repaired.')
print('Next: python -m pytest')
