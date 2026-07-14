from pathlib import Path
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent

def write(path: str, content: str):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')
    print(f'[WRITE] {path}')

def create_json(path: str, data):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(json.dumps(data, indent=2), encoding='utf-8')
        print(f'[CREATE] {path}')
    else:
        print(f'[SKIP] {path}')

print('=== Applying Buster v5.1 Perception Feed Repair ===')

write('buster/vision/perception_feed.py', r'''"""
Vision perception feed for Buster v5.1+.

This module converts vision/camera observations into lightweight perception
records that can be consumed by the perception loop, world model, mission
control, and tests.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any, Dict, List, Optional


DATA_DIR = Path('data')
DEFAULT_STATE_FILE = DATA_DIR / 'vision_perception_feed_state.json'
DEFAULT_OBSERVATION_FILE = DATA_DIR / 'vision_perception_feed_observations.json'


@dataclass
class VisionObservation:
    source: str = 'camera'
    kind: str = 'vision_observation'
    label: str = 'unknown'
    confidence: float = 0.0
    timestamp: str = ''
    metadata: Dict[str, Any] | None = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if not data.get('timestamp'):
            data['timestamp'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
        if data.get('metadata') is None:
            data['metadata'] = {}
        return data


class VisionPerceptionFeed:
    """Collects and normalizes vision observations for the Perception OS."""

    def __init__(self, state_file: str | Path = DEFAULT_STATE_FILE,
                 observations_file: str | Path = DEFAULT_OBSERVATION_FILE):
        self.state_file = Path(state_file)
        self.observations_file = Path(observations_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.observations_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self._write_json(self.state_file, {
                'enabled': True,
                'source': 'vision',
                'last_observation': None,
                'count': 0,
            })
        if not self.observations_file.exists():
            self._write_json(self.observations_file, [])

    def _read_json(self, path: Path, default: Any) -> Any:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return default
        return default

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def observe(self, label: str = 'unknown', confidence: float = 0.0,
                source: str = 'camera', metadata: Optional[Dict[str, Any]] = None,
                **extra: Any) -> Dict[str, Any]:
        meta = dict(metadata or {})
        meta.update(extra)
        obs = VisionObservation(
            source=source,
            label=label,
            confidence=float(confidence or 0.0),
            timestamp=datetime.now(timezone.utc).isoformat(timespec='seconds'),
            metadata=meta,
        ).to_dict()
        observations: List[Dict[str, Any]] = self._read_json(self.observations_file, [])
        observations.append(obs)
        self._write_json(self.observations_file, observations[-500:])
        state = self._read_json(self.state_file, {})
        state.update({
            'enabled': True,
            'source': 'vision',
            'last_observation': obs,
            'count': int(state.get('count', 0)) + 1,
            'updated': obs['timestamp'],
        })
        self._write_json(self.state_file, state)
        return obs

    def capture_observation(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return self.observe(*args, **kwargs)

    def latest(self) -> Optional[Dict[str, Any]]:
        state = self._read_json(self.state_file, {})
        return state.get('last_observation')

    def list_observations(self, limit: int = 50) -> List[Dict[str, Any]]:
        observations = self._read_json(self.observations_file, [])
        return observations[-limit:]

    def status(self) -> Dict[str, Any]:
        return self._read_json(self.state_file, {})
''')

# Also add a matching generic screen perception feed, because v5.1 tests/loops often expect both visual sources.
write('buster/perception/screen_feed.py', r'''"""Screen perception feed scaffold for Buster Perception OS."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any, Dict, List, Optional


class ScreenPerceptionFeed:
    def __init__(self, state_file: str | Path = 'data/screen_perception_feed_state.json',
                 observations_file: str | Path = 'data/screen_perception_feed_observations.json'):
        self.state_file = Path(state_file)
        self.observations_file = Path(observations_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.observations_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self._write_json(self.state_file, {'enabled': True, 'source': 'screen', 'last_observation': None, 'count': 0})
        if not self.observations_file.exists():
            self._write_json(self.observations_file, [])

    def _read_json(self, path: Path, default: Any) -> Any:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            pass
        return default

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def observe(self, app: str = 'unknown', title: str = '', metadata: Optional[Dict[str, Any]] = None, **extra: Any) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
        meta = dict(metadata or {})
        meta.update(extra)
        obs = {'source': 'screen', 'kind': 'screen_observation', 'app': app, 'title': title, 'timestamp': timestamp, 'metadata': meta}
        observations: List[Dict[str, Any]] = self._read_json(self.observations_file, [])
        observations.append(obs)
        self._write_json(self.observations_file, observations[-500:])
        state = self._read_json(self.state_file, {})
        state.update({'enabled': True, 'source': 'screen', 'last_observation': obs, 'count': int(state.get('count', 0)) + 1, 'updated': timestamp})
        self._write_json(self.state_file, state)
        return obs

    def latest(self):
        return self._read_json(self.state_file, {}).get('last_observation')

    def status(self):
        return self._read_json(self.state_file, {})
''')

create_json('data/vision_perception_feed_state.json', {'enabled': True, 'source': 'vision', 'last_observation': None, 'count': 0})
create_json('data/vision_perception_feed_observations.json', [])
create_json('data/screen_perception_feed_state.json', {'enabled': True, 'source': 'screen', 'last_observation': None, 'count': 0})
create_json('data/screen_perception_feed_observations.json', [])

print('\nSUCCESS: v5.1 missing VisionPerceptionFeed repaired.')
print('Next: python -m pytest')
